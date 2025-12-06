import React, { useState } from 'react';
import PropTypes from 'prop-types';

const VerificationForm = ({ onGenerate }) => {
    const [url, setUrl] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!url) {
            setError('Please enter a URL');
            return;
        }
        try {
            await onGenerate(url);
            setError('');
        } catch (err) {
            console.error(err);
            setError('Failed to generate session');
        }
    };

    return (
        <div className="card">
            <h2>Domain Verification</h2>
            <form onSubmit={handleSubmit}>
                <div className="input-group">
                    <input
                        type="url"
                        placeholder="Enter URL (e.g., https://gov.pl)"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        required
                    />
                </div>
                {error && <p className="error">{error}</p>}
                <button type="submit">Generuj QR Kod</button>
            </form>
        </div>
    );
};

VerificationForm.propTypes = {
    onGenerate: PropTypes.func.isRequired,
};

export default VerificationForm;
