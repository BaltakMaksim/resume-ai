// ===== Toast Notifications =====
function showToast(message, type = 'info', duration = 5000, title = null) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    
    const config = {
        error:   { icon: '❌', defaultTitle: 'Ошибка' },
        success: { icon: '✅', defaultTitle: 'Успешно' },
        warning: { icon: '⚠️', defaultTitle: 'Внимание' },
        info:    { icon: 'ℹ️', defaultTitle: 'Информация' }
    };
    
    const cfg = config[type] || config.info;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-icon">${cfg.icon}</div>
        <div class="toast-content">
            <div class="toast-title">${title || cfg.defaultTitle}</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" aria-label="Закрыть">✕</button>
        <div class="toast-progress" style="animation-duration: ${duration}ms"></div>
    `;
    
    container.appendChild(toast);
    
    const closeToast = () => {
        toast.classList.add('hiding');
        setTimeout(() => toast.remove(), 300);
    };
    
    toast.querySelector('.toast-close').addEventListener('click', closeToast);
    
    const timer = setTimeout(closeToast, duration);
    
    toast.addEventListener('mouseenter', () => {
        clearTimeout(timer);
        const progress = toast.querySelector('.toast-progress');
        if (progress) progress.style.animationPlayState = 'paused';
    });
    
    toast.addEventListener('mouseleave', () => {
        setTimeout(closeToast, 2000);
        const progress = toast.querySelector('.toast-progress');
        if (progress) progress.style.animationPlayState = 'running';
    });
    
    return toast;
}

const showError = (msg, duration = 6000) => showToast(msg, 'error', duration);
const showSuccess = (msg, duration = 4000) => showToast(msg, 'success', duration);
const showWarning = (msg, duration = 5000) => showToast(msg, 'warning', duration);
const showInfo = (msg, duration = 4000) => showToast(msg, 'info', duration);

// ===== DOM Elements =====
const uploadZone = document.getElementById('uploadZone');
const resumeInput = document.getElementById('resumeInput');
const fileNameDisplay = document.getElementById('fileName');
const githubInput = document.getElementById('githubInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const loading = document.getElementById('loading');
const results = document.getElementById('results');

const modeBtns = document.querySelectorAll('.mode-btn');
const fileMode = document.getElementById('fileMode');
const textMode = document.getElementById('textMode');
const resumeText = document.getElementById('resumeText');
const charCount = document.getElementById('charCount');

// ===== Mode Switch =====
modeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        modeBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        const mode = btn.dataset.mode;
        fileMode.style.display = mode === 'file' ? 'block' : 'none';
        textMode.style.display = mode === 'text' ? 'block' : 'none';
    });
});

// ===== Character Counter =====
if (resumeText && charCount) {
    resumeText.addEventListener('input', () => {
        const count = resumeText.value.length;
        charCount.textContent = count;
        
        const counterParent = charCount.parentElement;
        if (count >= 100) {
            counterParent.classList.add('valid');
            counterParent.classList.remove('invalid');
        } else {
            counterParent.classList.add('invalid');
            counterParent.classList.remove('valid');
        }
    });
}

// ===== Drag & Drop =====
if (uploadZone && resumeInput) {
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
        if (files.length > 0) {
            const file = files[0];
            const ext = file.name.split('.').pop().toLowerCase();
            
            if (ext === 'pdf' || ext === 'docx') {
                resumeInput.files = files;
                showFileName(file.name);
            } else if (ext === 'doc') {
                showError('Формат .doc устарел! Открой файл в Word и сохрани как .docx, или используй режим "📝 Вставить текст"');
            } else {
                showError('Поддерживаются только PDF и DOCX файлы. Или используй режим "📝 Вставить текст"');
            }
        }
    });

    resumeInput.addEventListener('change', (e) => {
        if (e.target.files[0]) {
            showFileName(e.target.files[0].name);
        }
    });
}

function showFileName(name) {
    fileNameDisplay.textContent = `✓ ${name}`;
    fileNameDisplay.classList.add('active');
}

// ===== Resume Analysis =====
analyzeBtn.addEventListener('click', analyze);

async function analyze() {
    const activeMode = document.querySelector('.mode-btn.active').dataset.mode;
    const formData = new FormData();
    
    if (activeMode === 'file') {
        if (!resumeInput.files[0]) {
            showError('Пожалуйста, выбери файл');
            return;
        }
        formData.append('resume', resumeInput.files[0]);
    } else {
        const text = resumeText.value.trim();
        if (text.length < 100) {
            showError(`Минимум 100 символов. Сейчас: ${text.length}`);
            resumeText.focus();
            return;
        }
        formData.append('resume_text', text);
    }
    
    formData.append('generate_audio', 'true');
    
    const githubValue = githubInput.value.trim();
    if (githubValue) {
        formData.append('github_username', githubValue);
    }
    
    loading.classList.add('active');
    results.classList.remove('active');
    results.innerHTML = '';
    analyzeBtn.disabled = true;
    
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Ошибка сервера');
        }
        
        const data = await response.json();
        displayResults(data.analysis, data.audio, data.github_profile);
        showSuccess('Анализ завершён успешно');
        
    } catch (error) {
        showError(error.message);
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

// ===== Display Results =====
function displayResults(analysis, audioBase64, githubProfile) {
    const results = document.getElementById('results');
    
    const hasGithub = githubProfile && !githubProfile.error && analysis.github_score !== null;
    const mainScore = hasGithub 
        ? (analysis.overall_score || 0) 
        : (analysis.resume_score || 0);
    
    const resumeScore = analysis.resume_score || 0;
    const githubScore = hasGithub ? (analysis.github_score || 0) : null;
    
    const circumference = 2 * Math.PI * 90;
    const offset = circumference - (mainScore / 10) * circumference;

    let html = `
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

        <div class="result-card">
            <div class="result-header">
                <div class="result-icon">💪</div>
                <div class="result-title">Сильные стороны</div>
            </div>
            <ul class="item-list success">
                ${(analysis.strengths || []).map(s => `<li>${s}</li>`).join('')}
            </ul>
        </div>

        <div class="result-card">
            <div class="result-header">
                <div class="result-icon">⚠️</div>
                <div class="result-title">Критические ошибки</div>
            </div>
            <ul class="item-list error">
                ${(analysis.critical_errors || []).map(e => `<li>${e}</li>`).join('')}
            </ul>
        </div>

        <div class="result-card">
            <div class="result-header">
                <div class="result-icon">🔑</div>
                <div class="result-title">Добавить keywords для ATS</div>
            </div>
            <ul class="item-list">
                ${(analysis.missing_keywords || []).map(k => `<li>${k}</li>`).join('')}
            </ul>
        </div>

        <div class="result-card">
            <div class="result-header">
                <div class="result-icon">📊</div>
                <div class="result-title">Анализ стека технологий</div>
            </div>
            <p style="font-size: 15px; line-height: 1.8; color: var(--text-secondary);">
                ${analysis.tech_stack_analysis || 'Нет данных'}
            </p>
        </div>

        <div class="result-card">
            <div class="advice-card">
                <h3>🎯 Совет для получения оффера</h3>
                <p>${analysis.advice_for_offer || 'Нет совета'}</p>
            </div>
        </div>
    `;

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

    setTimeout(() => {
        const progressCircle = results.querySelector('.progress');
        if (progressCircle) {
            progressCircle.style.strokeDashoffset = offset;
        }
    }, 100);

    results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ===== Cover Letter Logic =====
const clModeBtns = document.querySelectorAll('.cl-mode-btn');
const clFileInput = document.getElementById('clResumeInput');
const clFileName = document.getElementById('clFileName');
const generateClBtn = document.getElementById('generateClBtn');
const clResult = document.getElementById('clResult');
const clTextContent = document.getElementById('clTextContent');
const clAudioContainer = document.getElementById('clAudioContainer');
const clAudioPlayer = document.getElementById('clAudioPlayer');
const copyClBtn = document.getElementById('copyClBtn');

if (clModeBtns) {
    clModeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            clModeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const target = btn.dataset.target;
            document.getElementById('cl-file').style.display = target === 'cl-file' ? 'block' : 'none';
            document.getElementById('cl-text').style.display = target === 'cl-text' ? 'block' : 'none';
        });
    });
}

if (clFileInput) {
    clFileInput.addEventListener('change', (e) => {
        if (e.target.files[0]) {
            clFileName.textContent = `✓ ${e.target.files[0].name}`;
            clFileName.style.color = 'var(--ai-success)';
        }
    });
}

if (generateClBtn) {
    generateClBtn.addEventListener('click', async () => {
        const activeMode = document.querySelector('.cl-mode-btn.active').dataset.target;
        const company = document.getElementById('clCompany').value.trim();
        const jobDesc = document.getElementById('clJobDescription').value.trim();
        
        if (!company || !jobDesc) {
            showError('Заполни название компании и описание вакансии');
            return;
        }

        const formData = new FormData();
        formData.append('company_name', company);
        formData.append('job_description', jobDesc);
        formData.append('generate_audio', 'true');

        if (activeMode === 'cl-file') {
            if (!clFileInput.files[0]) {
                showError('Выбери файл резюме');
                return;
            }
            formData.append('resume', clFileInput.files[0]);
        } else {
            const text = document.getElementById('clResumeText').value.trim();
            if (text.length < 50) {
                showError('Вставь текст резюме (минимум 50 символов)');
                return;
            }
            formData.append('resume_text', text);
        }

        const originalText = generateClBtn.innerHTML;
        generateClBtn.innerHTML = '⏳ AI пишет письмо и озвучивает...';
        generateClBtn.disabled = true;
        clResult.style.display = 'none';

        try {
            const response = await fetch('/api/generate-cover-letter', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Ошибка генерации');
            }

            const data = await response.json();
            
            clTextContent.innerHTML = data.cover_letter.replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>');
            clResult.dataset.plainText = data.cover_letter;
            
            if (data.audio) {
                clAudioPlayer.src = `data:audio/mp3;base64,${data.audio}`;
                clAudioContainer.style.display = 'block';
            } else {
                clAudioContainer.style.display = 'none';
            }
            
            clResult.style.display = 'block';
            showSuccess('Сопроводительное письмо сгенерировано');
            clResult.scrollIntoView({ behavior: 'smooth', block: 'center' });

        } catch (error) {
            showError(error.message);
        } finally {
            generateClBtn.innerHTML = originalText;
            generateClBtn.disabled = false;
        }
    });
}

if (copyClBtn) {
    copyClBtn.addEventListener('click', () => {
        const text = clResult.dataset.plainText;
        navigator.clipboard.writeText(text).then(() => {
            showSuccess('Скопировано в буфер обмена');
        });
    });
}

// ===== Match Score Logic =====
const msModeBtns = document.querySelectorAll('.ms-mode-btn');
const msFileInput = document.getElementById('msResumeInput');
const msFileName = document.getElementById('msFileName');
const matchScoreBtn = document.getElementById('matchScoreBtn');
const msResult = document.getElementById('msResult');
const msScoreValue = document.getElementById('msScoreValue');
const msVerdict = document.getElementById('msVerdict');
const msSalary = document.getElementById('msSalary');
const msMatchReasons = document.getElementById('msMatchReasons');
const msGapReasons = document.getElementById('msGapReasons');
const msRecommendations = document.getElementById('msRecommendations');
const msAudioContainer = document.getElementById('msAudioContainer');
const msAudioPlayer = document.getElementById('msAudioPlayer');

if (msModeBtns) {
    msModeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            msModeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const target = btn.dataset.target;
            document.getElementById('ms-file').style.display = target === 'ms-file' ? 'block' : 'none';
            document.getElementById('ms-text').style.display = target === 'ms-text' ? 'block' : 'none';
        });
    });
}

if (msFileInput) {
    msFileInput.addEventListener('change', (e) => {
        if (e.target.files[0]) {
            msFileName.textContent = `✓ ${e.target.files[0].name}`;
            msFileName.style.color = 'var(--ai-success)';
        }
    });
}

if (matchScoreBtn) {
    matchScoreBtn.addEventListener('click', async () => {
        const activeMode = document.querySelector('.ms-mode-btn.active').dataset.target;
        const jobDesc = document.getElementById('msJobDescription').value.trim();
        
        if (!jobDesc || jobDesc.length < 50) {
            showError('Вставь описание вакансии (минимум 50 символов)');
            return;
        }

        const formData = new FormData();
        formData.append('job_description', jobDesc);
        formData.append('generate_audio', 'true');

        if (activeMode === 'ms-file') {
            if (!msFileInput.files[0]) {
                showError('Выбери файл резюме');
                return;
            }
            formData.append('resume', msFileInput.files[0]);
        } else {
            const text = document.getElementById('msResumeText').value.trim();
            if (text.length < 50) {
                showError('Вставь текст резюме (минимум 50 символов)');
                return;
            }
            formData.append('resume_text', text);
        }

        const originalText = matchScoreBtn.innerHTML;
        matchScoreBtn.innerHTML = '⏳ AI оценивает соответствие...';
        matchScoreBtn.disabled = true;
        msResult.style.display = 'none';

        try {
            const response = await fetch('/api/match-score', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Ошибка анализа');
            }

            const data = await response.json();
            const match = data.match_score;
            
            const score = match.match_score || 0;
            msScoreValue.textContent = `${score}%`;
            
            const circumference = 2 * Math.PI * 80;
            const offset = circumference - (score / 100) * circumference;
            
            const progressCircle = msResult.querySelector('.progress-match');
            if (progressCircle) {
                progressCircle.style.strokeDashoffset = circumference;
                progressCircle.style.stroke = '';
                
                setTimeout(() => {
                    progressCircle.style.transition = 'stroke-dashoffset 1.5s cubic-bezier(0.4, 0, 0.2, 1)';
                    progressCircle.style.strokeDashoffset = offset;
                    
                    if (score >= 70) {
                        progressCircle.style.stroke = 'var(--ai-success)';
                        progressCircle.style.filter = 'drop-shadow(0 0 20px rgba(0, 255, 136, 0.6))';
                    } else if (score >= 40) {
                        progressCircle.style.stroke = 'var(--ai-warning)';
                        progressCircle.style.filter = 'drop-shadow(0 0 20px rgba(255, 170, 0, 0.6))';
                    } else {
                        progressCircle.style.stroke = 'var(--ai-danger)';
                        progressCircle.style.filter = 'drop-shadow(0 0 20px rgba(255, 0, 85, 0.6))';
                    }
                }, 100);
            }
            
            msVerdict.textContent = match.verdict || 'Нет вердикта';
            msVerdict.className = 'ms-verdict';
            if (score >= 70) msVerdict.classList.add('high');
            else if (score >= 40) msVerdict.classList.add('medium');
            else msVerdict.classList.add('low');
            
            if (match.salary_estimate) {
                msSalary.innerHTML = `💰 <strong>Оценка зарплаты:</strong> ${match.salary_estimate}`;
                msSalary.style.display = 'block';
            } else {
                msSalary.style.display = 'none';
            }
            
            msMatchReasons.innerHTML = '';
            (match.match_reasons || []).forEach(reason => {
                const li = document.createElement('li');
                li.textContent = reason;
                msMatchReasons.appendChild(li);
            });
            
            msGapReasons.innerHTML = '';
            (match.gap_reasons || []).forEach(reason => {
                const li = document.createElement('li');
                li.textContent = reason;
                msGapReasons.appendChild(li);
            });
            
            msRecommendations.innerHTML = '';
            (match.recommendations || []).forEach(rec => {
                const li = document.createElement('li');
                li.textContent = rec;
                msRecommendations.appendChild(li);
            });
            
            if (data.audio) {
                msAudioPlayer.src = `data:audio/mp3;base64,${data.audio}`;
                msAudioContainer.style.display = 'block';
            } else {
                msAudioContainer.style.display = 'none';
            }
            
            msResult.style.display = 'block';
            showSuccess('Анализ соответствия завершён');
            msResult.scrollIntoView({ behavior: 'smooth', block: 'center' });

        } catch (error) {
            showError(error.message);
        } finally {
            matchScoreBtn.innerHTML = originalText;
            matchScoreBtn.disabled = false;
        }
    });
}

// ===== Mobile Navigation =====
const navToggle = document.getElementById('navToggle');
const navLinks = document.querySelector('.nav-links');

if (navToggle) {
    navToggle.addEventListener('click', () => {
        navLinks.classList.toggle('active');
    });
}

// Close mobile menu when clicking on a link
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', () => {
        navLinks.classList.remove('active');
    });
});

// ===== Active Navigation Highlighting =====
// ===== Active Navigation Highlighting =====
const sections = document.querySelectorAll('.section');
const navLinksArray = document.querySelectorAll('.nav-link');
const navHeight = 80; // Высота навигации + отступ

function updateActiveNav() {
    const scrollPosition = window.scrollY + navHeight + 100; // 100px offset для лучшего определения
    
    let currentSection = '';
    
    sections.forEach(section => {
        const sectionTop = section.offsetTop;
        const sectionHeight = section.offsetHeight;
        
        // Проверяем, находится ли секция в viewport
        if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
            currentSection = section.getAttribute('id');
        }
    });
    
    // Если дошли до конца страницы — подсвечиваем последнюю секцию
    if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 100) {
        currentSection = sections[sections.length - 1].getAttribute('id');
    }
    
    // Обновляем активные ссылки
    navLinksArray.forEach(link => {
        link.classList.remove('active');
        const linkSection = link.getAttribute('href').slice(1); // Убираем #
        
        if (linkSection === currentSection) {
            link.classList.add('active');
        }
    });
}

// Вызываем при скролле
window.addEventListener('scroll', updateActiveNav);

// Вызываем при загрузке страницы
window.addEventListener('load', updateActiveNav);

// Вызываем при клике на ссылку (после скролла)
navLinksArray.forEach(link => {
    link.addEventListener('click', () => {
        setTimeout(updateActiveNav, 500); // Задержка для завершения анимации скролла
    });
});