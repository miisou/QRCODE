import React, { useEffect, useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import PropTypes from 'prop-types';

const QRCodeDisplay = ({ value, expiresAt, onExpire }) => {
    const [timeLeft, setTimeLeft] = useState(0);

    useEffect(() => {
        const calculateTimeLeft = () => {
            const difference = +new Date(expiresAt * 1000) - +new Date();
            // Actually expiresAt is seconds from now or absolute timestamp?
            // Backend returns `expires_in` (seconds). 
            // We should have calculated target time in parent.
            // Let's assume parent passes `expiresIn` seconds, and we set target.
            // Or parent passes absolute expiration.
            // Let's assume parent handled it. 
            // If parent passes `expiresIn` (e.g. 30), we need to track it.
            // Let's change prop to `expiresIn` for simplicity.
        };
    }, []);

    // Simpler: Parent passes expiresIn. We start a countdown locally.
    // If backend returns 30, we count down 30.
};
// Wait, rewriting component to be simpler.

const QRCodeDisplaySimple = ({ value, initialTtl, onExpire }) => {
    const [timeLeft, setTimeLeft] = useState(initialTtl);

    useEffect(() => {
        if (timeLeft <= 0) {
            onExpire();
            return;
        }
        const timer = setInterval(() => {
            setTimeLeft((prev) => prev - 1);
        }, 1000);
        return () => clearInterval(timer);
    }, [timeLeft, onExpire]);

    return (
        <div className="card qr-container">
            <h3>Scan using Government App</h3>
            <div className="qr-wrapper">
                <QRCodeSVG value={value} size={256} />
            </div>
            <p>Time remaining: {timeLeft}s</p>
        </div>
    );
};

QRCodeDisplaySimple.propTypes = {
    value: PropTypes.string.isRequired,
    initialTtl: PropTypes.number.isRequired,
    onExpire: PropTypes.func.isRequired,
};

export default QRCodeDisplaySimple;
