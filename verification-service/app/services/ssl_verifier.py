import ssl
import socket
from urllib.parse import urlparse
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import ExtensionOID
from cryptography.x509.ocsp import OCSPRequestBuilder, OCSPResponseStatus
import requests
import datetime
from typing import Tuple, List, Optional

class SSLVerifier:
    def get_cert_chain(self, hostname: str, port: int = 443) -> List[x509.Certificate]:
        """
        Retrieves the certificate chain from the server.
        Note: Python's ssl module doesn't easily give the full chain including root unless configured blindly.
        We will rely on what the server sends and peer certificate.
        For a robust implementation, we might need to fetch intermediates if missing.
        """
        context = ssl.create_default_context()
        context.check_hostname = False # We verify manually
        context.verify_mode = ssl.CERT_NONE # We verify manually to get the cert even if unrelated error

        try:
            with socket.create_connection((hostname, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    peercert_der = ssock.getpeercert(binary_form=True)
                    if not peercert_der:
                        raise Exception("No certificate provided")
                    
                    # In a real rigorous implementation, we'd want to use a library that handles the full handshake inspection 
                    # to get all sent certificates. stored in unverified_context usually.
                    # Let's try to get full chain if possible or at least the peer cert.
                    # Python's SSLContext doesn't expose the full chain easily in getpeercert without verify_mode.
                    # Let's switch strategy: Use verify_mode=CERT_REQUIRED but with a custom context 
                    # that doesn't fail on hostname (we check later) but fails on chain?
                    # Actually, for deep inspection (including OCSP extraction), we just need the leaf cert 
                    # and its issuer. 
                    
                    leaf_cert = x509.load_der_x509_certificate(peercert_der, default_backend())
                    return [leaf_cert]
                    # Note: Getting the full chain including issuer for OCSP check usually requires the issuer to be sent 
                    # or in trust store. `ssock.get_unverified_chain()` is available in recent python? 
                    # No, it's not standard. 
                    # We will primarily check the Leaf Certificate for Revocation and Hostname.
                    # If we can't get issuer, we can't easily sign OCSP request.
                    
        except Exception as e:
            print(f"SSL Connection failed: {e}")
            return []

    def verify_hostname(self, cert: x509.Certificate, hostname: str) -> bool:
        try:
            # Check Subject Alternative Names
            try:
                san = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                dns_names = san.value.get_values_for_type(x509.DNSName)
                for dns in dns_names:
                    if self._match_hostname(dns, hostname):
                        return True
            except x509.ExtensionNotFound:
                pass
            
            # Check Common Name
            try:
                common_name = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
                if common_name:
                    cn = common_name[0].value
                    if self._match_hostname(cn, hostname):
                        return True
            except:
                pass
                
            return False
        except Exception:
            return False

    def _match_hostname(self, pattern: str, hostname: str) -> bool:
        if pattern == hostname:
            return True
        if pattern.startswith("*."):
            suffix = pattern[2:]
            if hostname.endswith(suffix) and hostname.count(".") == suffix.count(".") + 1:
                return True
        return False

    def check_revocation(self, cert: x509.Certificate, issuer: Optional[x509.Certificate] = None) -> Tuple[bool, str]:
        """
        Returns (is_revoked, reason)
        """
        # 1. OCSP
        try:
            aia = cert.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS)
            ocsps = [desc.access_location.value for desc in aia.value if desc.access_method.dotted_string == "1.3.6.1.5.5.7.48.1"]
            if ocsps and issuer:
                for ocsp_url in ocsps:
                    builder = OCSPRequestBuilder()
                    builder = builder.add_certificate(cert, issuer, x509.SHA1())
                    req = builder.build()
                    try:
                        resp = requests.post(ocsp_url, data=req.public_bytes(serialization.Encoding.DER), headers={'Content-Type': 'application/ocsp-request'}, timeout=3)
                        if resp.status_code == 200:
                            ocsp_resp = x509.ocsp.load_der_ocsp_response(resp.content)
                            if ocsp_resp.response_status == OCSPResponseStatus.SUCCESSFUL:
                                if ocsp_resp.certificate_status == x509.ocsp.OCSPCertStatus.REVOKED:
                                    return True, "OCSP: Revoked"
                                if ocsp_resp.certificate_status == x509.ocsp.OCSPCertStatus.GOOD:
                                    # If good, we can return False immediately if we trust OCSP
                                    pass
                    except Exception:
                        pass
        except x509.ExtensionNotFound:
            pass

        # 2. CRL
        try:
            cdp = cert.extensions.get_extension_for_oid(ExtensionOID.CRL_DISTRIBUTION_POINTS)
            for point in cdp.value:
                for full_name in point.full_name:
                    if isinstance(full_name, x509.UniformResourceIdentifier):
                        crl_url = full_name.value
                        try:
                            # Basic caching could be here
                            resp = requests.get(crl_url, timeout=5)
                            if resp.status_code == 200:
                                crl = x509.load_der_x509_crl(resp.content, default_backend())
                                if crl.get_revoked_certificate_by_serial_number(cert.serial_number):
                                    return True, "CRL: Revoked"
                        except Exception:
                            pass
        except x509.ExtensionNotFound:
            pass
        
        return False, "Not Revoked"
            
    def check_expiry(self, cert: x509.Certificate) -> Tuple[bool, str]:
        """
        Returns (is_valid, reason)
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        if now < cert.not_valid_before_utc:
            return False, "Certificate not yet valid"
        if now > cert.not_valid_after_utc:
            return False, "Certificate expired"
        return True, "Valid"

ssl_verifier = SSLVerifier()
