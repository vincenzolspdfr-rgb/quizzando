const data = window.GEOMETRIA_DATA;

const elements = {
  contestGate: document.querySelector('#contestGate'),
  contestSelect: document.querySelector('#contestSelect'),
  chooseContestBtn: document.querySelector('#chooseContestBtn'),
  studyControls: document.querySelector('#studyControls'),
  quizSection: document.querySelector('#quizSection'),
  subjectSelect: document.querySelector('#subjectSelect'),
  topicSelect: document.querySelector('#topicSelect'),
  limitSelect: document.querySelector('#limitSelect'),
  modeSelect: document.querySelector('#modeSelect'),
  shuffleToggle: document.querySelector('#shuffleToggle'),
  startBtn: document.querySelector('#startBtn'),
  reviewBtn: document.querySelector('#reviewBtn'),
  scoreCount: document.querySelector('#scoreCount'),
  topicLabel: document.querySelector('#topicLabel'),
  progressLabel: document.querySelector('#progressLabel'),
  progressBar: document.querySelector('#progressBar'),
  questionId: document.querySelector('#questionId'),
  questionText: document.querySelector('#questionText'),
  answers: document.querySelector('#answers'),
  feedback: document.querySelector('#feedback'),
  prevBtn: document.querySelector('#prevBtn'),
  nextBtn: document.querySelector('#nextBtn'),
  revealBtn: document.querySelector('#revealBtn'),
  favoriteBtn: document.querySelector('#favoriteBtn'),
  resetProgressBtn: document.querySelector('#resetProgressBtn'),
  wrongCount: document.querySelector('#wrongCount'),
  selectionTotalCount: document.querySelector('#selectionTotalCount'),
  selectionAnsweredCount: document.querySelector('#selectionAnsweredCount'),
  selectionCorrectCount: document.querySelector('#selectionCorrectCount'),
  selectionWrongCount: document.querySelector('#selectionWrongCount'),
};

const state = {
  session: [],
  index: 0,
  selected: false,
  responses: {},
  optionOrders: {},
  score: 0,
  completed: 0,
  wrong: [],
};

const STORAGE_KEY = 'vfpQuizProgress:v1';
const CONTEST_STORAGE_KEY = 'vfpQuizContest:v1';
const DATE_TOPIC_VALUE = '__date_timeline__';
const CONSTITUTIONAL_DATE_TOPIC_VALUE = '__constitutional_dates__';
const CONSTITUTIONAL_TERMS_TOPIC_VALUE = '__constitutional_terms__';
const questionsById = new Map(data.questions.map((question) => [question.id, question]));
let progress = loadProgress();

function showStudyApp() {
  elements.contestGate.classList.add('app-section-hidden');
  elements.studyControls.classList.remove('app-section-hidden');
}

function showQuizPanels() {
  elements.quizSection.classList.remove('app-section-hidden');
}

function loadContestSelection() {
  if (localStorage.getItem(CONTEST_STORAGE_KEY)) {
    showStudyApp();
  }
}

function chooseContest() {
  localStorage.setItem(CONTEST_STORAGE_KEY, elements.contestSelect.value);
  showStudyApp();
}

function loadProgress() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    const wrongIds = Array.isArray(saved.wrongIds)
      ? saved.wrongIds.filter((id, index, array) => questionsById.has(id) && array.indexOf(id) === index)
      : [];
    const perQuestion = saved.perQuestion && typeof saved.perQuestion === 'object' ? saved.perQuestion : {};
    for (const id of wrongIds) {
      if (!perQuestion[id]) {
        perQuestion[id] = { attempts: 1, correct: 0, wrong: 1, lastResult: 'wrong' };
      }
    }
    return {
      answered: Number(saved.answered) || 0,
      correct: Number(saved.correct) || 0,
      wrongIds,
      favoriteIds: Array.isArray(saved.favoriteIds)
        ? saved.favoriteIds.filter((id, index, array) => questionsById.has(id) && array.indexOf(id) === index)
        : [],
      perQuestion,
    };
  } catch {
    return { answered: 0, correct: 0, wrongIds: [], favoriteIds: [], perQuestion: {} };
  }
}

function saveProgress() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
}

function getWrongQuestions() {
  return progress.wrongIds.map((id) => questionsById.get(id)).filter(Boolean);
}

function getFavoriteQuestions() {
  return progress.favoriteIds.map((id) => questionsById.get(id)).filter(Boolean);
}

function getQuestionProgress(questionId) {
  return progress.perQuestion[questionId] || { attempts: 0, correct: 0, wrong: 0 };
}

function isFavorite(questionId) {
  return progress.favoriteIds.includes(questionId);
}

function toggleFavorite(questionId) {
  if (!questionsById.has(questionId)) {
    return;
  }
  if (isFavorite(questionId)) {
    progress.favoriteIds = progress.favoriteIds.filter((id) => id !== questionId);
  } else {
    progress.favoriteIds.push(questionId);
  }
  saveProgress();
  updateStats();
  updateFavoriteButton();
}

function resetProgress() {
  if (!confirm('Vuoi azzerare progressi, errori e preferite?')) {
    return;
  }
  progress = { answered: 0, correct: 0, wrongIds: [], favoriteIds: [], perQuestion: {} };
  saveProgress();
  state.session = [];
  state.index = 0;
  state.selected = false;
  state.score = 0;
  state.completed = 0;
  state.wrong = [];
  updateStats();
  renderQuestion();
}

function recordProgress(question, isCorrect) {
  progress.answered += 1;
  const current = getQuestionProgress(question.id);
  progress.perQuestion[question.id] = {
    attempts: current.attempts + 1,
    correct: current.correct + (isCorrect ? 1 : 0),
    wrong: current.wrong + (isCorrect ? 0 : 1),
    lastResult: isCorrect ? 'correct' : 'wrong',
    lastAnsweredAt: new Date().toISOString(),
  };
  if (isCorrect) {
    progress.correct += 1;
    progress.wrongIds = progress.wrongIds.filter((id) => id !== question.id);
  } else if (!progress.wrongIds.includes(question.id)) {
    progress.wrongIds.push(question.id);
  }
  saveProgress();
}

function shuffle(items) {
  const copy = [...items];
  for (let index = copy.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(Math.random() * (index + 1));
    [copy[index], copy[randomIndex]] = [copy[randomIndex], copy[index]];
  }
  return copy;
}

function normalizeAnswer(answer) {
  return answer.trim().toLowerCase().replace(/\s+/g, ' ');
}

function romanToNumber(value) {
  const map = { I: 1, V: 5, X: 10, L: 50, C: 100, D: 500, M: 1000 };
  return value.toUpperCase().split('').reduce((total, char, index, chars) => {
    const current = map[char] || 0;
    const next = map[chars[index + 1]] || 0;
    return total + (current < next ? -current : current);
  }, 0);
}

function extractDateInfo(question) {
  if (!['Storia', 'Letteratura'].includes(question.subject)) {
    return null;
  }

  const text = `${question.question} ${question.answer}`;
  const hasDateContext = /\b(anno|anni|data|date|secolo|nacque|nato|morì|morto|visse|governò|regnò|dal|al|nel|tra|fino|avvenne|avvenuto|fondata|fondato|incoronato|combattuta|combattuto|periodo|età|concilio|battaglia|guerra|pace|impero|imperatore)\b/i.test(text);
  const yearMatch = text.match(/\b(\d{3,4})\s*(a\.c\.|a\. c\.|avanti cristo|d\.c\.|d\. c\.|dopo cristo)?\b/i);
  if (yearMatch && hasDateContext) {
    const rawYear = Number(yearMatch[1]);
    const suffix = yearMatch[2] || '';
    const isBeforeChrist = /a\.\s*c\.|avanti cristo/i.test(suffix);
    return {
      value: isBeforeChrist ? -rawYear : rawYear,
      label: `${yearMatch[1]}${suffix ? ` ${suffix}` : ''}`.replace(/\s+/g, ' ').trim(),
    };
  }

  const centuryMatch = text.match(/\b([IVXLCDM]{1,6})\s*(?:°|º)?\s*(secolo|sec\.)\s*(a\.c\.|a\. c\.|avanti cristo|d\.c\.|d\. c\.|dopo cristo)?\b/i);
  if (centuryMatch) {
    const century = romanToNumber(centuryMatch[1]);
    const suffix = centuryMatch[3] || '';
    const midpoint = ((century - 1) * 100) + 50;
    const isBeforeChrist = /a\.\s*c\.|avanti cristo/i.test(suffix);
    return {
      value: isBeforeChrist ? -midpoint : midpoint,
      label: `${centuryMatch[1]} secolo${suffix ? ` ${suffix}` : ''}`.replace(/\s+/g, ' ').trim(),
    };
  }

  return null;
}

function extractConstitutionalDateInfo(question) {
  if (question.subject !== 'Costituzionale') {
    return null;
  }

  const text = `${question.question} ${question.answer}`;
  const hasInstitutionalContext = /\b(costituzione|repubblica|referendum|assemblea costituente|costituente|entrata in vigore|promulgata|approvata|trattato|unione europea|maastricht|lisbona|nazioni unite|onu|elezioni politiche|suffragio)\b/i.test(text);
  if (!hasInstitutionalContext) {
    return null;
  }

  const questionAsksDate = /\b(in quale anno|in che anno|quando|in quale data|data|fu firmata il|fu approvata|fu promulgata|nasce nel|istituita nel|entrata in vigore)\b/i.test(question.question);
  const answerHasDate = /\b(18\d{2}|19\d{2}|20\d{2})\b|\b\d{1,2}\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\b/i.test(question.answer);
  if (!questionAsksDate && !answerHasDate) {
    return null;
  }

  const yearMatch = question.answer.match(/\b(18\d{2}|19\d{2}|20\d{2})\b/) || text.match(/\b(18\d{2}|19\d{2}|20\d{2})\b/);
  if (!yearMatch) {
    return null;
  }

  return {
    value: Number(yearMatch[1]),
    label: yearMatch[1],
  };
}

function extractConstitutionalTermInfo(question) {
  if (question.subject !== 'Costituzionale') {
    return null;
  }

  const text = `${question.question} ${question.answer}`;
  const hasTermContext = /\b(mandato|carica|durata|legislatura|resta in carica|rimane in carica|eletto per|eletti per|scade|termine|entro|anni di età|maggiore età|età minima)\b/i.test(text);
  if (!hasTermContext) {
    return null;
  }

  const durationMatch = text.match(/\b(\d{1,2})\s*(anni|anno|mesi|mese|giorni|giorno)\b/i);
  if (!durationMatch) {
    return null;
  }

  const amount = Number(durationMatch[1]);
  const unit = durationMatch[2].toLowerCase();
  const value = unit.startsWith('ann') ? amount * 365 : unit.startsWith('mes') ? amount * 30 : amount;

  return {
    value,
    label: `${durationMatch[1]} ${durationMatch[2]}`,
  };
}

function createOptions(currentQuestion) {
  if (!state.optionOrders[currentQuestion.id]) {
    state.optionOrders[currentQuestion.id] = shuffle(currentQuestion.options);
  }
  return state.optionOrders[currentQuestion.id];
}

function getSubjectSelection() {
  const selectedSubject = elements.subjectSelect.value;
  return data.questions.filter((question) => selectedSubject === 'all' || question.subject === selectedSubject);
}

function getBaseSelection() {
  const selectedSubject = elements.subjectSelect.value;
  const selectedTopic = elements.topicSelect.value;
  return data.questions.filter((question) => {
    const subjectMatches = selectedSubject === 'all' || question.subject === selectedSubject;
    const specialTopic = selectedTopic === DATE_TOPIC_VALUE || selectedTopic === CONSTITUTIONAL_DATE_TOPIC_VALUE || selectedTopic === CONSTITUTIONAL_TERMS_TOPIC_VALUE;
    const topicMatches = selectedTopic === 'all' || specialTopic || question.topic === selectedTopic;
    return subjectMatches && topicMatches;
  });
}

function getDateTimelineQuestions(questions) {
  return questions
    .map((question) => ({ question, dateInfo: extractDateInfo(question) }))
    .filter((item) => item.dateInfo)
    .sort((first, second) => first.dateInfo.value - second.dateInfo.value || Number(first.question.id) - Number(second.question.id))
    .map((item) => item.question);
}

function getConstitutionalDateQuestions(questions) {
  return questions
    .map((question) => ({ question, dateInfo: extractConstitutionalDateInfo(question) }))
    .filter((item) => item.dateInfo)
    .sort((first, second) => first.dateInfo.value - second.dateInfo.value || Number(first.question.id) - Number(second.question.id))
    .map((item) => item.question);
}

function getConstitutionalTermQuestions(questions) {
  return questions
    .map((question) => ({ question, termInfo: extractConstitutionalTermInfo(question) }))
    .filter((item) => item.termInfo)
    .sort((first, second) => first.termInfo.value - second.termInfo.value || Number(first.question.id) - Number(second.question.id))
    .map((item) => item.question);
}

function getSelectedTopicQuestions() {
  const selectedTopic = elements.topicSelect.value;
  const questions = getBaseSelection();
  if (selectedTopic === DATE_TOPIC_VALUE) {
    return getDateTimelineQuestions(questions);
  }
  if (selectedTopic === CONSTITUTIONAL_DATE_TOPIC_VALUE) {
    return getConstitutionalDateQuestions(questions);
  }
  if (selectedTopic === CONSTITUTIONAL_TERMS_TOPIC_VALUE) {
    return getConstitutionalTermQuestions(questions);
  }
  return questions;
}

function applyModeFilter(questions) {
  const selectedTopic = elements.topicSelect.value;
  const baseQuestions = selectedTopic === DATE_TOPIC_VALUE
    ? getDateTimelineQuestions(questions)
    : selectedTopic === CONSTITUTIONAL_DATE_TOPIC_VALUE
      ? getConstitutionalDateQuestions(questions)
      : selectedTopic === CONSTITUTIONAL_TERMS_TOPIC_VALUE
        ? getConstitutionalTermQuestions(questions)
        : questions;
  switch (elements.modeSelect.value) {
    case 'unanswered':
      return baseQuestions.filter((question) => getQuestionProgress(question.id).attempts === 0);
    case 'wrong':
      return baseQuestions.filter((question) => progress.wrongIds.includes(question.id));
    case 'correct':
      return baseQuestions.filter((question) => {
        const item = getQuestionProgress(question.id);
        return item.correct > 0 && !progress.wrongIds.includes(question.id);
      });
    case 'favorite':
      return baseQuestions.filter((question) => progress.favoriteIds.includes(question.id));
    default:
      return baseQuestions;
  }
}

function populateSubjects() {
  elements.subjectSelect.innerHTML = '';
  elements.subjectSelect.add(new Option(`Tutte le materie (${data.total})`, 'all'));
  for (const subject of data.subjects) {
    const count = data.countsBySubject[subject] || 0;
    elements.subjectSelect.add(new Option(`${subject} (${count})`, subject));
  }
  populateTopics();
}

function populateTopics() {
  const selectedSubject = elements.subjectSelect.value;
  elements.topicSelect.innerHTML = '';
  elements.topicSelect.add(new Option('Tutti i sotto-argomenti', 'all'));

  const topics = selectedSubject === 'all'
    ? data.subjects.flatMap((subject) => data.topicsBySubject[subject] || [])
    : data.topicsBySubject[selectedSubject] || [];

  for (const topic of topics) {
    const count = data.questions.filter((question) => {
      const subjectMatches = selectedSubject === 'all' || question.subject === selectedSubject;
      return subjectMatches && question.topic === topic;
    }).length;
    elements.topicSelect.add(new Option(`${topic} (${count})`, topic));
  }

  const dateCount = getDateTimelineQuestions(getSubjectSelection()).length;
  if (dateCount > 0) {
    elements.topicSelect.add(new Option(`Solo date - linea temporale (${dateCount})`, DATE_TOPIC_VALUE));
  }

  const constitutionalDateCount = getConstitutionalDateQuestions(getSubjectSelection()).length;
  if (constitutionalDateCount > 0) {
    elements.topicSelect.add(new Option(`Date storiche costituzionali (${constitutionalDateCount})`, CONSTITUTIONAL_DATE_TOPIC_VALUE));
  }

  const constitutionalTermCount = getConstitutionalTermQuestions(getSubjectSelection()).length;
  if (constitutionalTermCount > 0) {
    elements.topicSelect.add(new Option(`Durate, mandati e termini (${constitutionalTermCount})`, CONSTITUTIONAL_TERMS_TOPIC_VALUE));
  }
  updateStats();
}

function buildSession(sourceQuestions = null) {
  const selectedSubject = elements.subjectSelect.value;
  const selectedTopic = elements.topicSelect.value;
  const limit = elements.limitSelect.value;
  let questions = sourceQuestions || applyModeFilter(getBaseSelection());
  showQuizPanels();

  const orderedSpecialTopic = selectedTopic === DATE_TOPIC_VALUE || selectedTopic === CONSTITUTIONAL_DATE_TOPIC_VALUE || selectedTopic === CONSTITUTIONAL_TERMS_TOPIC_VALUE;
  if (elements.shuffleToggle.checked && !orderedSpecialTopic) {
    questions = shuffle(questions);
  }

  if (limit !== 'all') {
    questions = questions.slice(0, Number(limit));
  }

  state.session = questions;
  state.index = 0;
  state.selected = false;
  state.responses = {};
  state.optionOrders = {};
  state.score = 0;
  state.completed = 0;
  state.wrong = [];
  updateStats();
  renderQuestion();
}

function renderQuestion() {
  elements.answers.innerHTML = '';
  elements.feedback.className = 'feedback hidden';
  elements.feedback.textContent = '';
  elements.prevBtn.disabled = state.index <= 0;
  elements.nextBtn.disabled = state.session.length === 0;
  elements.revealBtn.disabled = state.session.length === 0;
  elements.favoriteBtn.disabled = state.session.length === 0;
  state.selected = false;

  if (state.session.length === 0) {
    elements.topicLabel.textContent = 'Nessuna domanda disponibile';
    elements.progressLabel.textContent = '0 / 0';
    elements.progressBar.style.width = '0%';
    elements.questionId.textContent = 'N domanda';
    elements.questionText.textContent = 'Non ci sono domande per questa selezione.';
    elements.prevBtn.disabled = true;
    elements.nextBtn.disabled = true;
    elements.favoriteBtn.disabled = true;
    return;
  }

  if (state.index >= state.session.length) {
    renderFinished();
    return;
  }

  const currentQuestion = state.session[state.index];
  const dateInfo = extractDateInfo(currentQuestion) || extractConstitutionalDateInfo(currentQuestion) || extractConstitutionalTermInfo(currentQuestion);
  const progress = Math.round((state.index / state.session.length) * 100);
  elements.topicLabel.textContent = dateInfo
    ? `${currentQuestion.subject} · ${currentQuestion.topic} · ${dateInfo.label}`
    : `${currentQuestion.subject} · ${currentQuestion.topic}`;
  elements.progressLabel.textContent = `${state.index + 1} / ${state.session.length}`;
  elements.progressBar.style.width = `${progress}%`;
  elements.questionId.textContent = `N domanda ${currentQuestion.id}`;
  elements.questionText.textContent = currentQuestion.question;
  updateFavoriteButton();

  for (const option of createOptions(currentQuestion)) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'answer-btn';
    button.textContent = option;
    button.addEventListener('click', () => selectAnswer(button, option));
    elements.answers.append(button);
  }

  renderStoredResponse(currentQuestion);
}

function renderStoredResponse(currentQuestion) {
  const storedResponse = state.responses[currentQuestion.id];
  if (!storedResponse) {
    return;
  }

  state.selected = true;
  for (const answerButton of elements.answers.querySelectorAll('.answer-btn')) {
    answerButton.disabled = true;
    const isCorrectAnswer = normalizeAnswer(answerButton.textContent) === normalizeAnswer(currentQuestion.answer);
    const isSelectedAnswer = storedResponse.selectedAnswer && normalizeAnswer(answerButton.textContent) === normalizeAnswer(storedResponse.selectedAnswer);
    if (isCorrectAnswer) {
      answerButton.classList.add('correct');
    }
    if (!storedResponse.isCorrect && isSelectedAnswer) {
      answerButton.classList.add('wrong');
    }
  }

  elements.feedback.className = storedResponse.isCorrect ? 'feedback good' : 'feedback bad';
  elements.feedback.textContent = storedResponse.isCorrect ? 'Risposta corretta.' : `Risposta corretta: ${currentQuestion.answer}`;
  elements.revealBtn.disabled = true;
}

function selectAnswer(button, selectedAnswer) {
  if (state.selected) {
    return;
  }

  state.selected = true;
  state.completed += 1;
  const currentQuestion = state.session[state.index];
  const isCorrect = normalizeAnswer(selectedAnswer) === normalizeAnswer(currentQuestion.answer);
  state.responses[currentQuestion.id] = { selectedAnswer, isCorrect };

  for (const answerButton of elements.answers.querySelectorAll('.answer-btn')) {
    answerButton.disabled = true;
    if (normalizeAnswer(answerButton.textContent) === normalizeAnswer(currentQuestion.answer)) {
      answerButton.classList.add('correct');
    }
  }

  if (isCorrect) {
    state.score += 1;
    elements.feedback.className = 'feedback good';
    elements.feedback.textContent = 'Risposta corretta.';
  } else {
    button.classList.add('wrong');
    state.wrong.push(currentQuestion);
    elements.feedback.className = 'feedback bad';
    elements.feedback.textContent = `Risposta corretta: ${currentQuestion.answer}`;
  }

  recordProgress(currentQuestion, isCorrect);
  elements.nextBtn.disabled = false;
  elements.revealBtn.disabled = true;
  updateStats();
}

function revealAnswer() {
  if (state.selected || state.session.length === 0 || state.index >= state.session.length) {
    return;
  }
  const currentQuestion = state.session[state.index];
  state.selected = true;
  state.completed += 1;
  state.wrong.push(currentQuestion);
  state.responses[currentQuestion.id] = { selectedAnswer: null, isCorrect: false };

  for (const answerButton of elements.answers.querySelectorAll('.answer-btn')) {
    answerButton.disabled = true;
    if (normalizeAnswer(answerButton.textContent) === normalizeAnswer(currentQuestion.answer)) {
      answerButton.classList.add('correct');
    }
  }

  elements.feedback.className = 'feedback bad';
  elements.feedback.textContent = `Risposta corretta: ${currentQuestion.answer}`;
  recordProgress(currentQuestion, false);
  elements.nextBtn.disabled = false;
  elements.revealBtn.disabled = true;
  updateStats();
}

function nextQuestion() {
  state.index += 1;
  renderQuestion();
}

function renderFinished() {
  elements.topicLabel.textContent = 'Quiz completato';
  elements.progressLabel.textContent = `${state.session.length} / ${state.session.length}`;
  elements.progressBar.style.width = '100%';
  elements.questionId.textContent = 'Fine sessione';
  elements.questionText.textContent = `Hai risposto correttamente a ${state.score} domande su ${state.session.length}.`;
  elements.answers.innerHTML = '';
  elements.feedback.className = 'feedback good';
  elements.feedback.textContent = state.wrong.length === 0 ? 'Nessun errore in questa sessione.' : 'Puoi ripassare solo le domande sbagliate.';
  elements.nextBtn.disabled = true;
  elements.revealBtn.disabled = true;
  elements.reviewBtn.disabled = getWrongQuestions().length === 0;
  elements.favoriteBtn.disabled = true;
  elements.prevBtn.disabled = state.session.length === 0;
}

function previousQuestion() {
  if (state.index <= 0) {
    return;
  }
  state.index -= 1;
  renderQuestion();
}

function updateStats() {
  updateSessionStats();
  updateSelectionStats();
}

function updateSessionStats() {
  elements.scoreCount.textContent = state.score;
  elements.wrongCount.textContent = state.wrong.length;
  elements.reviewBtn.disabled = getWrongQuestions().length === 0;
}

function updateSelectionStats() {
  const questions = getSelectedTopicQuestions();
  const totals = questions.reduce((accumulator, question) => {
    const item = getQuestionProgress(question.id);
    accumulator.answered += item.attempts > 0 ? 1 : 0;
    accumulator.correct += item.lastResult === 'correct' ? 1 : 0;
    accumulator.wrong += item.lastResult === 'wrong' ? 1 : 0;
    return accumulator;
  }, { answered: 0, correct: 0, wrong: 0 });
  elements.selectionTotalCount.textContent = questions.length;
  elements.selectionAnsweredCount.textContent = totals.answered;
  elements.selectionCorrectCount.textContent = totals.correct;
  elements.selectionWrongCount.textContent = totals.wrong;
}

function updateFavoriteButton() {
  if (state.session.length === 0 || state.index >= state.session.length) {
    elements.favoriteBtn.disabled = true;
    elements.favoriteBtn.textContent = 'Preferita';
    elements.favoriteBtn.classList.remove('active-favorite');
    return;
  }
  const currentQuestion = state.session[state.index];
  const active = isFavorite(currentQuestion.id);
  elements.favoriteBtn.disabled = false;
  elements.favoriteBtn.textContent = active ? 'Preferita salvata' : 'Preferita';
  elements.favoriteBtn.classList.toggle('active-favorite', active);
}

function reviewWrong() {
  const wrongQuestions = getWrongQuestions();
  if (wrongQuestions.length === 0) {
    return;
  }
  buildSession(wrongQuestions);
}

function handleKeyboardShortcuts(event) {
  const activeTag = document.activeElement?.tagName?.toLowerCase();
  if (activeTag === 'input' || activeTag === 'select' || activeTag === 'textarea') {
    return;
  }

  if (event.key === 'ArrowRight') {
    event.preventDefault();
    if (!elements.nextBtn.disabled) {
      nextQuestion();
    }
    return;
  }

  if (event.key === 'ArrowLeft') {
    event.preventDefault();
    if (!elements.prevBtn.disabled) {
      previousQuestion();
    }
    return;
  }

  if (/^[1-4]$/.test(event.key)) {
    const answerButtons = Array.from(elements.answers.querySelectorAll('.answer-btn'));
    const button = answerButtons[Number(event.key) - 1];
    if (button && !button.disabled) {
      event.preventDefault();
      button.click();
    }
  }
}

populateSubjects();
loadContestSelection();
elements.subjectSelect.addEventListener('change', populateTopics);
elements.topicSelect.addEventListener('change', updateStats);
elements.chooseContestBtn.addEventListener('click', chooseContest);
elements.startBtn.addEventListener('click', () => buildSession());
elements.prevBtn.addEventListener('click', previousQuestion);
elements.nextBtn.addEventListener('click', nextQuestion);
elements.revealBtn.addEventListener('click', revealAnswer);
elements.favoriteBtn.addEventListener('click', () => {
  if (state.session.length > 0 && state.index < state.session.length) {
    toggleFavorite(state.session[state.index].id);
  }
});
elements.reviewBtn.addEventListener('click', reviewWrong);
elements.resetProgressBtn.addEventListener('click', resetProgress);
document.addEventListener('keydown', handleKeyboardShortcuts);
updateStats();
renderQuestion();
