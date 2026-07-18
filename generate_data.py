from pathlib import Path
import json
import re
import fitz

BASE = Path(__file__).resolve().parent.parent
SOURCE_PDF = BASE / 'vfp-banca-dati-quesiti.pdf'
GEOMETRY_TOPICS_DIR = BASE / 'argomenti'
OUT = Path(__file__).resolve().parent / 'questions.js'

SUBJECT_RANGES = {
    'Costituzionale': (2, 47, 1, 760),
    'Geografia': (47, 69, 761, 1215),
    'Grammatica': (69, 106, 1216, 1966),
    'Informatica': (106, 131, 1967, 2341),
    'Inglese': (131, 163, 2342, 3043),
    'Letteratura': (163, 203, 3044, 3800),
    'Aritmetica': (203, 225, 3801, 4180),
    'Geometria': (225, 248, 4181, 4562),
    'Scienze': (248, 266, 4563, 4867),
    'Storia': (266, 306, 4868, 5620),
    'Tecnologia': (306, 327, 5621, 6000),
}

HISTORY_TOPIC_RULES = [
    ('Storia antica: Grecia, Roma e popoli antichi', [
        'sparta', 'atene', 'greci', 'grecia', 'romani', 'roma', 'etruschi', 'cartagine',
        'puniche', 'cesare', 'augusto', 'traiano', 'diocleziano', 'costantino', 'impero romano',
        'senato', 'patrizi', 'plebei', 'repubblica romana', 'alessandro magno', 'macedone',
        'egizi', 'mesopotamia', 'persiani', 'sumeri', 'babilonesi', 'fenici', 'iliade', 'odissea',
    ]),
    ('Medioevo: regni, Chiesa, comuni e crociate', [
        'medioevo', 'medievale', 'teodorico', 'cassiodoro', 'boezio', 'ostrogoti', 'giustiniano',
        'longobardi', 'alboino', 'franchi', 'carlo magno', 'poitiers', 'feudalesimo', 'feudo',
        'vassallo', 'comuni', 'crociate', 'islam', 'maometto', 'arabi', 'bizantino', 'normanni',
        'federico ii', 'melfitane', 'papato', 'chiesa', 'monachesimo', 'benedetto', 'investiture',
        'guelfi', 'ghibellini', 'venezia', 'genova', 'visconti', 'signorie', 'peste nera',
    ]),
    ('Rinascimento, scoperte geografiche e Riforma', [
        'rinascimento', 'umanesimo', 'medici', 'lorenzo de', 'leonardo', 'michelangelo', 'machiavelli',
        'galileo', 'colombo', 'vespucci', 'magellano', 'caboto', 'america', 'nuovo mondo',
        'scoperte geografiche', 'luter', 'riforma', 'controriforma', 'concilio di trento',
        'calvino', 'anglicana', 'carlo v', 'enrico viii',
    ]),
    ('Età moderna: assolutismo, Illuminismo e rivoluzioni', [
        'assolutismo', 'luigi xiv', 'illuminismo', 'illuministi', 'rivoluzione industriale',
        'rivoluzione americana', 'rivoluzione francese', 'napoleone', 'robespierre', 'giacobini',
        'congresso di vienna', 'restaurazione', 'settecento', 'ancien régime', 'monarchia assoluta',
        'locke', 'montesquieu', 'voltaire', 'rousseau',
    ]),
    ('Risorgimento e Italia unita', [
        'risorgimento', 'mazzini', 'garibaldi', 'cavour', 'vittorio emanuele', 'savoia',
        "unità d'italia", 'italia unita', 'carbonari', 'moti del', "prima guerra d'indipendenza",
        "seconda guerra d'indipendenza", "terza guerra d'indipendenza", 'breccia di porta pia',
        "regno d'italia", 'statuto albertino', 'destra storica', 'sinistra storica',
    ]),
    ('Novecento: guerre mondiali, fascismo e guerra fredda', [
        'prima guerra mondiale', 'grande guerra', 'seconda guerra mondiale', 'fascismo', 'mussolini',
        'nazismo', 'hitler', 'olocausto', 'resistenza', 'partigiani', 'repubblica sociale',
        'guerra fredda', 'urss', 'stati uniti', 'nato', 'patto di varsavia', 'muro di berlino',
        'onu', 'ventennio', 'marcia su roma', 'leggi razziali', 'liberazione',
    ]),
    ('Istituzioni, cittadinanza e storia contemporanea', [
        'costituzione', 'repubblica italiana', 'parlamento', 'presidente della repubblica',
        'governo', 'democrazia', 'referendum', 'unione europea', 'europa unita', 'trattato',
        'diritti', 'suffragio', 'cittadinanza', 'res publica',
    ]),
]

LITERATURE_TOPIC_RULES = [
    ('Dante, Medioevo e origini della letteratura', [
        'dante', 'divina commedia', 'inferno', 'purgatorio', 'paradiso', 'beatrice', 'virgilio',
        'dolce stil novo', 'stilnovo', 'cavalcanti', 'guinizzelli', 'francesco d\'assisi',
        'jacopone', 'medioevo', 'scuola siciliana', 'federico ii', 'boccaccio', 'decameron',
        'petrarca', 'canzoniere', 'laura',
    ]),
    ('Umanesimo, Rinascimento e Barocco', [
        'umanesimo', 'rinascimento', 'ariosto', 'orlando furioso', 'tasso', 'gerusalemme liberata',
        'machiavelli', 'il principe', 'guicciardini', 'boiardo', 'poliziano', 'pulci', 'barocco',
        'marino', 'secentismo', 'accademia della crusca',
    ]),
    ('Settecento, Illuminismo e Neoclassicismo', [
        'illuminismo', 'illuminista', 'parini', 'goldoni', 'alfieri', 'neoclassicismo', 'foscolo',
        'ortis', 'sepolcri', 'arcadia', 'settecento', 'metastasio', 'beccaria',
    ]),
    ('Ottocento: Romanticismo, Leopardi, Manzoni e Verismo', [
        'romanticismo', 'romantico', 'leopardi', 'zibaldone', 'manzoni', 'promessi sposi',
        'renzo', 'lucia', 'don abbondio', 'don rodrigo', 'innominato', 'verga', 'verismo',
        'malavoglia', 'mastro-don gesualdo', 'risorgimento', 'carducci', 'scapigliatura',
    ]),
    ('Novecento: Decadentismo, avanguardie e autori contemporanei', [
        'novecento', 'decadentismo', 'pascoli', 'd\'annunzio', 'pirandello', 'svevo', 'ungaretti',
        'montale', 'saba', 'ermetismo', 'futurismo', 'marinetti', 'crepuscolare', 'calvino',
        'moravia', 'primo levi', 'quasimodo', 'gadda', 'pavese', 'vittorini', 'sciascia',
    ]),
    ('Generi letterari e tecniche narrative', [
        'romanzo', 'racconto', 'novella', 'favola', 'fiaba', 'fantasy', 'giallo', 'poema',
        'poesia', 'lirica', 'teatro', 'commedia', 'tragedia', 'narratore', 'protagonista',
        'personaggio', 'soliloquio', 'monologo', 'flusso di coscienza', 'discorso indiretto',
        'fabula', 'intreccio', 'sequenza', 'flashback', 'analessi', 'prolessi',
    ]),
    ('Metrica, retorica e analisi del testo', [
        'metrica', 'verso', 'strofa', 'sonetto', 'endecasillabo', 'settenario', 'rima', 'enjambement',
        'similitudine', 'metafora', 'sinestesia', 'ossimoro', 'anafora', 'allitterazione',
        'personificazione', 'iperbole', 'retorica', 'onomatopea', 'chiasmo', 'climax',
    ]),
]

SUBJECT_TOPIC_RULES = {
    'Costituzionale': [
        ('Principi fondamentali e diritti costituzionali', ['costituzione', 'art.', 'articolo', 'diritto', 'diritti', 'dovere', 'uguaglianza', 'libertà', 'lavoro', 'religione', 'stampa', 'salute', 'istruzione']),
        ('Parlamento, Governo e Presidente della Repubblica', ['parlamento', 'camera', 'senato', 'governo', 'ministro', 'presidente della repubblica', 'consiglio dei ministri', 'fiducia', 'decreto', 'legge']),
        ('Magistratura, giustizia e Corte costituzionale', ['magistratura', 'giudice', 'giudici', 'processo', 'pena', 'reato', 'corte costituzionale', 'consiglio superiore', 'csm', 'giurisdizione']),
        ('Regioni, enti locali e pubblica amministrazione', ['regione', 'regioni', 'comune', 'provincia', 'sindaco', 'giunta', 'statuto speciale', 'pubblica amministrazione', 'ente locale']),
        ('Unione Europea e ordinamento internazionale', ['unione europea', 'ue', 'trattato', 'nazioni unite', 'onu', 'internazionale', 'europea']),
    ],
    'Geografia': [
        ('Italia fisica e politica', ['italia', 'italiano', 'italiana', 'regione', 'capoluogo', 'provincia', 'appennini', 'alpi', 'po ', 'tevere', 'lazio', 'sicilia', 'sardegna']),
        ('Europa', ['europa', 'europeo', 'francia', 'spagna', 'germania', 'regno unito', 'portogallo', 'grecia', 'balcani', 'danubio', 'renania']),
        ('Continenti e stati del mondo', ['asia', 'africa', 'america', 'oceania', 'australia', 'cina', 'india', 'giappone', 'brasile', 'canada', 'stati uniti', 'russia']),
        ('Geografia fisica: monti, fiumi, mari e clima', ['fiume', 'lago', 'mare', 'oceano', 'monte', 'montagna', 'catena', 'clima', 'deserto', 'isola', 'penisola', 'vulcano']),
        ('Economia, popolazione e geografia umana', ['popolazione', 'abitanti', 'densità', 'economia', 'agricoltura', 'industria', 'turismo', 'capitale', 'città']),
    ],
    'Grammatica': [
        ('Ortografia, accenti e punteggiatura', ['ortografia', 'errore', 'accento', 'apostrofo', 'punteggiatura', 'maiuscola', 'minuscola', 'hanno', 'anno']),
        ('Morfologia: nomi, articoli, aggettivi e pronomi', ['nome', 'nomi', 'articolo', 'aggettivo', 'pronome', 'pronomi', 'genere', 'numero', 'singolare', 'plurale']),
        ('Verbi, modi e tempi verbali', ['verbo', 'verbi', 'indicativo', 'congiuntivo', 'condizionale', 'imperativo', 'participio', 'gerundio', 'infinito', 'tempo']),
        ('Analisi logica e sintassi', ['soggetto', 'predicato', 'complemento', 'analisi logica', 'proposizione', 'periodo', 'subordinata', 'coordinata', 'principale']),
        ('Lessico, sinonimi, contrari e significato', ['sinonimo', 'contrario', 'significa', 'significato', 'lessico', 'parola', 'termine', 'etimologia']),
    ],
    'Informatica': [
        ('Hardware, periferiche e memoria', ['hardware', 'cpu', 'processore', 'ram', 'memoria', 'hard disk', 'scheda', 'monitor', 'stampante', 'mouse', 'tastiera']),
        ('Software, sistemi operativi e file', ['software', 'sistema operativo', 'windows', 'linux', 'file', 'cartella', 'programma', 'applicazione', 'driver']),
        ('Internet, reti e posta elettronica', ['internet', 'rete', 'web', 'browser', 'email', 'e-mail', 'posta elettronica', 'url', 'http', 'wifi', 'router']),
        ('Office, documenti e fogli di calcolo', ['word', 'excel', 'powerpoint', 'foglio di calcolo', 'documento', 'testo', 'cella', 'formula', 'presentazione']),
        ('Sicurezza informatica e dati', ['password', 'virus', 'malware', 'backup', 'privacy', 'sicurezza', 'antivirus', 'crittografia', 'phishing']),
    ],
    'Inglese': [
        ('Verbi, tempi e forme verbali', ['verb', 'past', 'present', 'future', 'tense', 'to be', 'to have', 'going to', 'will', 'do', 'does', 'did']),
        ('Lessico e traduzione', ['translate', 'meaning', 'means', 'word', 'synonym', 'opposite', 'fruit', 'work', 'house', 'school']),
        ('Preposizioni, articoli e pronomi', ['preposition', 'article', 'pronoun', 'some', 'any', 'much', 'many', 'who', 'which', 'where']),
        ('Frasi, dialoghi e comprensione', ['complete', 'sentence', 'dialogue', 'question', 'answer', 'choose', 'conversation']),
        ('Comparativi, modali e strutture grammaticali', ['comparative', 'superlative', 'can', 'could', 'must', 'should', 'would', 'if', 'than']),
    ],
    'Aritmetica': [
        ('Numeri, operazioni e proprietà', ['somma', 'differenza', 'prodotto', 'quoziente', 'numero', 'numeri', 'multiplo', 'divisibile', 'potenza', 'quadrato', 'cubo']),
        ('Frazioni, decimali e percentuali', ['frazione', 'frazioni', 'decimale', 'percentuale', '%', 'per cento', 'rapporto']),
        ('Equazioni, problemi e proporzioni', ['equazione', 'incognita', 'proporzione', 'proporzionale', 'problema', 'determina', 'calcola']),
        ('Geometria numerica e misure', ['area', 'perimetro', 'metro', 'cm', 'dm', 'litro', 'peso', 'misura']),
        ('Probabilità, media e statistica', ['probabilità', 'media', 'statistica', 'estratto', 'tombola', 'dado', 'urna']),
    ],
    'Scienze': [
        ('Fisica, energia e materia', ['energia', 'forza', 'massa', 'peso', 'velocità', 'temperatura', 'calore', 'pressione', 'materia', 'atomo']),
        ('Chimica e sostanze', ['chimica', 'elemento', 'molecola', 'ossigeno', 'idrogeno', 'carbonio', 'acqua', 'soluzione', 'acido', 'base']),
        ('Biologia: cellule, corpo umano e salute', ['cellula', 'cellule', 'organismo', 'sangue', 'cuore', 'polmoni', 'apparato', 'digestivo', 'respiratorio', 'dna', 'virus']),
        ('Terra, ambiente e astronomia', ['terra', 'sole', 'luna', 'pianeta', 'stelle', 'atmosfera', 'clima', 'ambiente', 'ecosistema', 'rocce']),
        ('Botanica e zoologia', ['pianta', 'piante', 'animale', 'animali', 'fiore', 'foglia', 'vertebrati', 'mammiferi', 'insetti']),
    ],
    'Tecnologia': [
        ('Disegno tecnico, scale e misure', ['scala', 'cartina', 'distanza', 'disegno', 'misura', 'proiezione', 'quotatura']),
        ('Materiali e lavorazioni', ['materiale', 'materiali', 'legno', 'carta', 'vetro', 'metallo', 'plastica', 'ceramica', 'tessile', 'fibra']),
        ('Energia, elettricità e impianti', ['energia', 'elettrica', 'corrente', 'alternatore', 'fotovoltaico', 'pannello', 'centrale', 'impianto', 'petrolio']),
        ('Meccanica, macchine e strutture', ['macchina', 'motore', 'leva', 'ruota', 'ingranaggio', 'forza', 'compressione', 'trazione', 'struttura']),
        ('Informatica e comunicazioni tecnologiche', ['computer', 'digitale', 'telecomunicazioni', 'internet', 'rete', 'segnale', 'satellite']),
    ],
}


def clean_text(text):
    text = re.sub(r'\s+([,.;:?!°])', r'\1', text)
    text = re.sub(r'\s+', ' ', text)
    replacements = ["l' ", "L' ", "dell' ", "all' ", "un' ", "Un' ", "d' ", "D' "]
    for token in replacements:
        text = text.replace(token, token.strip())
    return text.strip()


def usable_lines(page_text, subject):
    for line in page_text.splitlines():
        text = line.strip()
        if not text:
            continue
        if text == subject.upper():
            continue
        if text == 'BANCA DATI':
            continue
        if re.fullmatch(r'\d+\s+di\s+\d+', text):
            continue
        yield line


def extract_subject_records(subject, start_page, end_page, first_id, last_id):
    with fitz.open(str(SOURCE_PDF)) as doc:
        subject_text = '\n'.join(
            '\n'.join(usable_lines(doc[page_index].get_text(), subject))
            for page_index in range(start_page, end_page)
        )

    records = []
    current_id = None
    current_lines = []
    for line in subject_text.splitlines():
        match = re.match(r'^(\d{1,4})\.\s*(.*)', line)
        if match and first_id <= int(match.group(1)) <= last_id:
            if current_id is not None:
                records.append(parse_record(subject, current_id, '\n'.join(current_lines)))
            current_id = match.group(1)
            current_lines = [match.group(2)]
        elif current_id is not None:
            current_lines.append(line)
    if current_id is not None:
        records.append(parse_record(subject, current_id, '\n'.join(current_lines)))
    return records


def parse_record(subject, quiz_id, body):
        parts = re.split(r'(?m)^([ABCD])\)\s*', body)
        question = clean_text(parts[0])
        options = {}
        for index in range(1, len(parts), 2):
            options[parts[index]] = clean_text(parts[index + 1])
        if set(options) != {'A', 'B', 'C', 'D'}:
            raise SystemExit(f'Opzioni incomplete per {subject} {quiz_id}: {sorted(options)}')
        return {
            'id': quiz_id,
            'subject': subject,
            'question': question,
            'answer': options['A'],
            'options': [options['A'], options['B'], options['C'], options['D']],
        }


def geometry_topic_map():
    mapping = {}
    order = []
    for path in sorted(GEOMETRY_TOPICS_DIR.glob('*.txt')):
        if path.name.startswith('00_'):
            continue
        content = path.read_text(encoding='utf-8')
        title = content.splitlines()[0].strip()
        order.append(title)
        for quiz_id in re.findall(r'(?m)^([0-9]{4})\s+', content):
            mapping[quiz_id] = title
    return mapping, order


def classify_history_topic(record):
    haystack = f"{record['question']} {record['answer']} {' '.join(record['options'])}".lower()
    for topic, keywords in HISTORY_TOPIC_RULES:
        if any(keyword in haystack for keyword in keywords):
            return topic
    return 'Storia generale e domande miste'


def classify_literature_topic(record):
    haystack = f"{record['question']} {record['answer']} {' '.join(record['options'])}".lower()
    for topic, keywords in LITERATURE_TOPIC_RULES:
        if any(keyword in haystack for keyword in keywords):
            return topic
    return 'Letteratura generale e domande miste'


def classify_by_rules(record, rules, fallback):
    haystack = f"{record['question']} {record['answer']} {' '.join(record['options'])}".lower()
    for topic, keywords in rules:
        if any(keyword in haystack for keyword in keywords):
            return topic
    return fallback


def classify_topic(record, geometry_topics_by_id):
    if record['subject'] == 'Geometria':
        return geometry_topics_by_id.get(record['id'], 'Varie, definizioni e quiz misti')
    if record['subject'] == 'Storia':
        return classify_history_topic(record)
    if record['subject'] == 'Letteratura':
        return classify_literature_topic(record)
    return classify_by_rules(
        record,
        SUBJECT_TOPIC_RULES.get(record['subject'], []),
        f"{record['subject']} generale e domande miste",
    )


def validate_questions(questions):
    empty_answers = [item['id'] for item in questions if not item['answer']]
    bad_options = [
        item['id'] for item in questions
        if len(item['options']) != 4
    ]
    missing_correct = [
        item['id'] for item in questions
        if item['answer'].strip().lower() not in {option.strip().lower() for option in item['options']}
    ]
    footer_dirty = [
        item['id'] for item in questions
        if any('BANCA DATI' in option or re.search(r'\b\d+ di \d+\b', option) for option in item['options'])
    ]
    if empty_answers:
        raise SystemExit(f'Risposte vuote: {empty_answers[:20]}')
    if bad_options:
        raise SystemExit(f'Opzioni mancanti: {bad_options[:20]}')
    if missing_correct:
        raise SystemExit(f'Risposta corretta non presente nelle opzioni: {missing_correct[:20]}')
    if footer_dirty:
        raise SystemExit(f'Footer PDF nelle opzioni: {footer_dirty[:20]}')


def main():
    geometry_topics_by_id, geometry_topic_order = geometry_topic_map()
    expected_counts = {
        'Costituzionale': 760,
        'Geografia': 455,
        'Grammatica': 751,
        'Informatica': 375,
        'Inglese': 702,
        'Letteratura': 757,
        'Aritmetica': 380,
        'Geometria': 382,
        'Scienze': 305,
        'Storia': 753,
        'Tecnologia': 380,
    }
    subject_order = [
        'Costituzionale',
        'Geografia',
        'Grammatica',
        'Informatica',
        'Inglese',
        'Letteratura',
        'Aritmetica',
        'Geometria',
        'Scienze',
        'Storia',
        'Tecnologia',
    ]
    questions = []
    topics_by_subject = {}
    counts_by_subject = {}

    for subject in subject_order:
        records = extract_subject_records(subject, *SUBJECT_RANGES[subject])
        if len(records) != expected_counts[subject]:
            raise SystemExit(f'{subject}: attese {expected_counts[subject]} domande, ottenute {len(records)}')
        counts_by_subject[subject] = len(records)
        topics_by_subject[subject] = []
        if subject == 'Geometria':
            topics_by_subject[subject] = geometry_topic_order.copy()
        for record in records:
            topic = classify_topic(record, geometry_topics_by_id)
            if topic not in topics_by_subject[subject]:
                topics_by_subject[subject].append(topic)
            questions.append({**record, 'topic': topic})

    validate_questions(questions)

    payload = {
        'generatedFrom': 'vfp-banca-dati-quesiti.pdf',
        'total': len(questions),
        'subjects': subject_order,
        'topicsBySubject': topics_by_subject,
        'countsBySubject': counts_by_subject,
        'questions': questions,
    }
    OUT.write_text('window.GEOMETRIA_DATA = ' + json.dumps(payload, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8')
    print(f'created {OUT}')
    print(f'total {len(questions)}')
    for subject in subject_order:
        print(f'{subject.lower()} {counts_by_subject[subject]}')
    print(f'subjects {len(subject_order)}')


if __name__ == '__main__':
    main()
