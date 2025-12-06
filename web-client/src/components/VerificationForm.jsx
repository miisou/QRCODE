import React, { useState } from 'react';
import PropTypes from 'prop-types';

const VerificationForm = ({ onGenerate }) => {
    const [error, setError] = useState('');

    const handleGenerate = async () => {
        try {
            await onGenerate();
            setError('');
        } catch (err) {
            console.error(err);
            setError('Failed to generate session');
        }
    };

    return (
        <div className="card">
            <h2>Domain Verification</h2>
            <p className="hint">Verify this website using the Govt App.</p>
            {error && <p className="error">{error}</p>}
            <button onClick={handleGenerate}>Generate QR Code</button>
        </div>
    );
};

VerificationForm.propTypes = {
    onGenerate: PropTypes.func.isRequired,
};

export default VerificationForm;
