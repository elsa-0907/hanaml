/**
 * SMS Spam Shield - Client-side Controller
 * Handles model health verification, user interaction, asynchronous prediction requests,
 * and secure result rendering.
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const smsInput = document.getElementById('sms-input');
  const charCounter = document.getElementById('char-counter');
  const analyzeBtn = document.getElementById('analyze-btn');
  const analyzeBtnText = document.getElementById('analyze-btn-text');
  const analyzeSpinner = document.getElementById('analyze-spinner');
  const clearBtn = document.getElementById('clear-btn');
  const errorBanner = document.getElementById('error-banner');
  const errorMessage = document.getElementById('error-message');
  const modelStatusPill = document.getElementById('model-status-pill');
  const modelStatusText = document.getElementById('model-status-text');

  // Result Elements
  const resultContainer = document.getElementById('result-container');
  const resultCard = document.getElementById('result-card');
  const resultHeading = document.getElementById('result-heading');
  const resultBadge = document.getElementById('result-badge');
  const resultIconSpam = document.getElementById('result-icon-spam');
  const resultIconHam = document.getElementById('result-icon-ham');
  const resultRecText = document.getElementById('result-recommendation-text');
  const resultMessageText = document.getElementById('result-message-text');
  const resultTimestamp = document.getElementById('result-timestamp');
  const resetResultBtn = document.getElementById('reset-result-btn');

  // Preset buttons
  const presetButtons = document.querySelectorAll('.preset-btn');

  // Preset Sample Messages for Testing
  const PRESET_MESSAGES = {
    'spam-urgent': 'URGENT! You have won a 1-week family holiday to Florida. Call 09012345678 now to claim. T&Cs apply.',
    'spam-phishing': 'Alert: Your bank account has been temporarily restricted due to unauthorized login. Verify at https://secure-bank-login.example.com/auth immediately.',
    'ham-friend': 'Hey, are you free for coffee later this afternoon around 4? Let me know!',
    'ham-delivery': 'Your package #92841 is out for delivery today between 2:00 PM and 5:00 PM. No signature required.'
  };

  /**
   * Updates live character counter display
   */
  function updateCharCount() {
    const count = smsInput.value.length;
    charCounter.textContent = `${count} / 1000 characters`;
    if (count > 1000) {
      charCounter.style.color = 'var(--color-warning)';
    } else {
      charCounter.style.color = 'var(--text-subtle)';
    }
  }

  /**
   * Displays an error alert banner with safe text rendering
   * @param {string} msg
   */
  function showError(msg) {
    errorMessage.textContent = msg;
    errorBanner.classList.remove('hidden');
  }

  /**
   * Clears the error alert banner
   */
  function hideError() {
    errorBanner.classList.add('hidden');
    errorMessage.textContent = '';
  }

  /**
   * Toggles the button loading state
   * @param {boolean} isLoading
   */
  function setLoadingState(isLoading) {
    if (isLoading) {
      analyzeBtn.disabled = true;
      smsInput.disabled = true;
      analyzeSpinner.classList.remove('hidden');
      analyzeBtnText.textContent = 'Analyzing...';
    } else {
      analyzeBtn.disabled = false;
      smsInput.disabled = false;
      analyzeSpinner.classList.add('hidden');
      analyzeBtnText.textContent = 'Analyze Message';
    }
  }

  /**
   * Formats ISO-8601 backend timestamp into human-readable local and UTC strings
   * @param {string} isoString
   * @returns {string}
   */
  function formatTimestamp(isoString) {
    try {
      const date = new Date(isoString);
      if (isNaN(date.getTime())) {
        return isoString || 'Just now';
      }
      const localStr = date.toLocaleString(undefined, {
        dateStyle: 'medium',
        timeStyle: 'medium'
      });
      return `${localStr} (${date.toISOString()})`;
    } catch {
      return isoString || 'Just now';
    }
  }

  /**
   * Checks backend model health and updates top-navigation status pill
   */
  async function checkModelHealth() {
    try {
      const response = await fetch('/api/health');
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      const data = await response.json();

      modelStatusPill.className = 'status-pill';
      if (data.model_loaded === true) {
        modelStatusPill.classList.add('status-ready');
        modelStatusText.textContent = 'Model Ready';
        modelStatusPill.title = `Loaded: ${data.model_type || 'TF-IDF + LinearSVC Pipeline'}`;
      } else {
        modelStatusPill.classList.add('status-degraded');
        modelStatusText.textContent = 'Model Offline';
        modelStatusPill.title = data.message || 'Model file not loaded on server.';
      }
    } catch (err) {
      modelStatusPill.className = 'status-pill status-offline';
      modelStatusText.textContent = 'Service Offline';
      modelStatusPill.title = 'Unable to reach backend health endpoint.';
    }
  }

  /**
   * Renders the prediction result returned by the backend
   * Uses textContent exclusively to prevent XSS vulnerabilities.
   * @param {Object} data
   */
  function renderPredictionResult(data) {
    const isSpam = (data.prediction || '').toLowerCase() === 'spam';

    // Reset card classes
    resultCard.classList.remove('is-spam', 'is-ham');

    if (isSpam) {
      resultCard.classList.add('is-spam');
      resultHeading.textContent = 'Potential Spam Detected';
      resultBadge.textContent = 'SPAM';
      resultIconSpam.classList.remove('hidden');
      resultIconHam.classList.add('hidden');
      resultRecText.textContent =
        'Be cautious. Avoid suspicious links and requests for passwords, OTPs, banking details, or other sensitive information.';
    } else {
      resultCard.classList.add('is-ham');
      resultHeading.textContent = 'No Spam Detected';
      resultBadge.textContent = 'HAM — classified as legitimate by the model';
      resultIconHam.classList.remove('hidden');
      resultIconSpam.classList.add('hidden');
      resultRecText.textContent =
        'A ham prediction indicates the model classified this as legitimate text, but this does not guarantee the message is safe. Always verify unexpected senders and never share sensitive credentials over unverified channels.';
    }

    // Safely insert analyzed message without raw innerHTML
    resultMessageText.textContent = data.message || smsInput.value;

    // Display backend timestamp
    resultTimestamp.textContent = formatTimestamp(data.timestamp);

    // Reveal result container
    resultContainer.classList.remove('hidden');

    // Smooth scroll to result
    setTimeout(() => {
      resultContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
  }

  /**
   * Handles submission and triggers prediction API request
   */
  async function handleAnalyze() {
    hideError();

    const text = smsInput.value.trim();

    // Client-side empty validation
    if (!text) {
      showError('Please enter an SMS message to analyze.');
      smsInput.focus();
      return;
    }

    setLoadingState(true);

    try {
      const response = await fetch('/api/predict', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: text })
      });

      const result = await response.json().catch(() => null);

      if (!response.ok) {
        const errorDetail = (result && result.error)
          ? result.error
          : `Server returned error (${response.status}).`;
        showError(errorDetail);
        return;
      }

      if (!result || !result.success) {
        showError((result && result.error) || 'Failed to analyze message.');
        return;
      }

      // Valid prediction received
      renderPredictionResult(result);

    } catch (networkErr) {
      showError('Network error: Unable to connect to the classification service. Please check your connection or server status.');
    } finally {
      setLoadingState(false);
    }
  }

  // Event Listeners
  smsInput.addEventListener('input', () => {
    updateCharCount();
    if (smsInput.value.trim().length > 0) {
      hideError();
    }
  });

  // Shortcut: Ctrl+Enter or Cmd+Enter to submit
  smsInput.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleAnalyze();
    }
  });

  // Clear button click
  clearBtn.addEventListener('click', () => {
    smsInput.value = '';
    updateCharCount();
    hideError();
    smsInput.focus();
  });

  // Analyze button click
  analyzeBtn.addEventListener('click', handleAnalyze);

  // Preset buttons click
  presetButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const presetKey = btn.getAttribute('data-preset');
      if (PRESET_MESSAGES[presetKey]) {
        smsInput.value = PRESET_MESSAGES[presetKey];
        updateCharCount();
        hideError();
        smsInput.focus();
      }
    });
  });

  // Reset/Analyze Another button click
  resetResultBtn.addEventListener('click', () => {
    resultContainer.classList.add('hidden');
    smsInput.value = '';
    updateCharCount();
    hideError();
    smsInput.focus();
    window.scrollTo({ top: smsInput.offsetTop - 100, behavior: 'smooth' });
  });

  // Initial setup
  updateCharCount();
  checkModelHealth();
});
