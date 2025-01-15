-- Création des tables dans l'ordre des dépendances

-- Table sources (utilisée dans main.py)
CREATE TABLE IF NOT EXISTS sources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    url VARCHAR(512) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table keywords (utilisée dans main.py)
CREATE TABLE IF NOT EXISTS keywords (
    id INT AUTO_INCREMENT PRIMARY KEY,
    value VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table filters (utilisée dans main.py)
CREATE TABLE IF NOT EXISTS filters (
    id INT PRIMARY KEY,
    exclude_ads BOOLEAN DEFAULT FALSE,
    exclude_professional BOOLEAN DEFAULT FALSE,
    target_press BOOLEAN DEFAULT FALSE,
    time_unit VARCHAR(50) DEFAULT 'mois',
    time_value INT DEFAULT 1,
    exclude_jobs BOOLEAN DEFAULT FALSE,
    exclude_training BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Table cache (utilisée dans main.py)
CREATE TABLE IF NOT EXISTS cache (
    input_hash VARCHAR(32) NOT NULL,
    result_key VARCHAR(255) NOT NULL,
    data LONGTEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (input_hash, result_key)
);

-- Table feedback (utilisée dans utils.py)
CREATE TABLE IF NOT EXISTS feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATETIME NOT NULL,
    onglet VARCHAR(255) NOT NULL,
    unite_temps VARCHAR(50),
    titre_reponse TEXT NOT NULL,
    contenu_reponse TEXT NOT NULL,
    reponse_urls TEXT,
    avis_utilisateur VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertion des valeurs par défaut pour filters
INSERT IGNORE INTO filters (id, exclude_ads, exclude_professional, target_press, time_unit, time_value, exclude_jobs, exclude_training)
VALUES (1, FALSE, FALSE, FALSE, 'mois', 1, FALSE, FALSE);