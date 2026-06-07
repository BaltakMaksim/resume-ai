// DOM Elements
const uploadZone = document.getElementById('uploadZone');
const resumeInput = document.getElementById('resumeInput');
const fileNameDisplay = document.getElementById('fileName');
const githubInput = document.getElementById('githubInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const loading = document.getElementById('loading');
const results = document.getElementById('results');

// Drag & Drop
uploadZone.addEventListener('click', () => resumeInput.click());

uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('dragover');
});

uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('dragover');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0 && files[0].type === 'application/pdf') {
        resumeInput.files = files;
        showFileName(files[0].name);
    }
});

resumeInput.addEventListener('change', (e) => {
    if (e.target.files[0]) {
        showFileName(e.target.files[0].name);
    }
});

function showFileName(name) {
    fileNameDisplay.textContent = `✓ ${name}`;
    fileNameDisplay.classList.add('active');
}

// Analysis
analyzeBtn.addEventListener('click', analyze);

async function analyze() {
    if (!resumeInput.files[0]) {
        alert('Пожалуйста, выбери PDF файл');
        return;
    }

    const formData = new FormData();
    formData.append('resume', resumeInput.files[0]);
    formData.append('generate_audio', 'true');

    // GitHub добавляем ТОЛЬКО если заполнен
    const githubValue = githubInput.value.trim();
    if (githubValue) {
        formData.append('github_username', githubValue);
    }

    loading.classList.add('active');
    results.classList.remove('active');
    results.innerHTML = '';
    analyzeBtn.disabled = true;

    try {
        const response = await fetch('http://localhost:8000/analyze', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Ошибка сервера');
        }

        const data = await response.json();
        displayResults(data.analysis, data.audio, data.github_profile);

    } catch (error) {
        results.innerHTML = `
            <div class="result-card">
                <div class="result-header">
                    <div class="result-icon">❌</div>
                    <div class="result-title">Ошибка</div>
                </div>
                <p>${error.message}</p>
            </div>
        `;
        results.classList.add('active');
    } finally {
        loading.classList.remove('active');
        analyzeBtn.disabled = false;
    }
}

function displayResults(analysis, audioBase64, githubProfile) {
    const results = document.getElementById('results');
    
    // Проверяем наличие GitHub данных
    const hasGithub = githubProfile && !githubProfile.error && analysis.github_score !== null;
    
    // Определяем основную оценку для круга
    const mainScore = hasGithub 
        ? (analysis.overall_score || 0) 
        : (analysis.resume_score || 0);
    
    // Оценки для детализации
    const resumeScore = analysis.resume_score || 0;
    const githubScore = hasGithub ? (analysis.github_score || 0) : null;
    
    const circumference = 2 * Math.PI * 90;
    const offset = circumference - (mainScore / 10) * circumference;

    let html = `
        <!-- Main Score Card -->
        <div class="result-card">
            <div class="score-display">
                <div class="score-circle">
                    <svg width="200" height="200">
                        <circle class="bg" cx="100" cy="100" r="90"></circle>
                        <circle class="progress" cx="100" cy="100" r="90" 
                            stroke-dasharray="${circumference}" 
                            stroke-dashoffset="${circumference}">
                        </circle>
                    </svg>
                    <div class="score-value">${mainScore}/10</div>
                </div>
                <div class="score-label">
                    ${hasGithub ? 'Общая оценка' : 'Оценка резюме'}
                </div>
                <div class="roast-text">"${analysis.roast || 'Нет комментария'}"</div>
            </div>
        </div>

        <!-- Scores Breakdown -->
        <div class="result-card">
            <div class="result-header">
                <div class="result-icon">📊</div>
                <div class="result-title">Детализация оценок</div>
            </div>
            <div class="scores-grid ${hasGithub ? '' : 'single-score'}">
                <div class="score-item">
                    <div class="score-item-value">${resumeScore}</div>
                    <div class="score-item-label">📄 Резюме</div>
                    <div class="score-item-desc">
                        ${resumeScore >= 7 ? 'Отличное резюме!' : 
                          resumeScore >= 5 ? 'Хорошо, но есть что улучшить' : 
                          'Нужна серьёзная доработка'}
                    </div>
                </div>
                
                ${hasGithub ? `
                <div class="score-item">
                    <div class="score-item-value">${githubScore}</div>
                    <div class="score-item-label">💻 GitHub</div>
                    <div class="score-item-desc">
                        ${githubScore >= 7 ? 'Активный профиль!' : 
                          githubScore >= 5 ? 'Есть потенциал' : 
                          'Мало активности'}
                    </div>
                </div>
                <div class="score-item total">
                    <div class="score-item-value">${mainScore}</div>
                    <div class="score-item-label">⭐ Итого</div>
                    <div class="score-item-desc">Средняя оценка</div>
                </div>
                ` : ''}
            </div>
        </div>

        <!-- Strengths -->
        <div class="result-card">
            <div class="result-header">
                <div class="result-icon">💪</div>
                <div class="result-title">Сильные стороны</div>
            </div>
            <ul class="item-list success">
                ${(analysis.strengths || []).map(s => `<li>${s}</li>`).join('')}
            </ul>
        </div>

        <!-- Critical Errors -->
        <div class="result-card">
            <div class="result-header">
                <div class="result-icon">⚠️</div>
                <div class="result-title">Критические ошибки</div>
            </div>
            <ul class="item-list error">
                ${(analysis.critical_errors || []).map(e => `<li>${e}</li>`).join('')}
            </ul>
        </div>

        <!-- Missing Keywords -->
        <div class="result-card">
            <div class="result-header">
                <div class="result-icon">🔑</div>
                <div class="result-title">Добавить keywords для ATS</div>
            </div>
            <ul class="item-list">
                ${(analysis.missing_keywords || []).map(k => `<li>${k}</li>`).join('')}
            </ul>
        </div>

        <!-- Tech Stack -->
        <div class="result-card">
            <div class="result-header">
                <div class="result-icon">📊</div>
                <div class="result-title">Анализ стека технологий</div>
            </div>
            <p style="font-size: 15px; line-height: 1.8; color: var(--text-secondary);">
                ${analysis.tech_stack_analysis || 'Нет данных'}
            </p>
        </div>

        <!-- Advice -->
        <div class="result-card">
            <div class="advice-card">
                <h3>🎯 Совет для получения оффера</h3>
                <p>${analysis.advice_for_offer || 'Нет совета'}</p>
            </div>
        </div>
    `;

    // Audio Player
    if (audioBase64) {
        html += `
            <div class="result-card">
                <div class="audio-section">
                    <div class="result-header">
                        <div class="result-icon">🔊</div>
                        <div class="result-title">Голосовой отчёт от AI HR</div>
                    </div>
                    <audio controls class="audio-player" style="width: 100%;">
                        <source src="data:audio/mp3;base64,${audioBase64}" type="audio/mpeg">
                        Ваш браузер не поддерживает аудио элемент.
                    </audio>
                    <div class="audio-text">"${analysis.tts_summary || ''}"</div>
                </div>
            </div>
        `;
    }

    results.innerHTML = html;
    results.classList.add('active');

    // Animate score circle
    setTimeout(() => {
        const progressCircle = results.querySelector('.progress');
        if (progressCircle) {
            progressCircle.style.strokeDashoffset = offset;
        }
    }, 100);

    results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}