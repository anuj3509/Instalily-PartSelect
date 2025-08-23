-- PartSelect RAG Database Schema
-- Read-optimized database for fast lookups and real data validation

-- Parts table - main product catalog
CREATE TABLE IF NOT EXISTS parts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_number TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    price REAL,
    brand TEXT,
    manufacturer TEXT,
    manufacturer_id INTEGER,
    category TEXT,
    image_url TEXT,
    product_url TEXT NOT NULL,
    installation_guide TEXT,
    installation_difficulty TEXT,
    installation_time TEXT,
    install_video_url TEXT,
    video_url TEXT,
    symptoms TEXT,
    product_types TEXT,
    replacement_parts TEXT,
    availability TEXT,
    in_stock BOOLEAN DEFAULT TRUE,
    specifications TEXT, -- JSON string
    data_type TEXT DEFAULT 'json_part', -- 'json_part', 'csv_part', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Compatibility table - which parts work with which models
CREATE TABLE IF NOT EXISTS part_compatibility (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_number TEXT NOT NULL,
    model_number TEXT NOT NULL,
    brand TEXT,
    appliance_type TEXT, -- 'refrigerator' or 'dishwasher'
    FOREIGN KEY (part_number) REFERENCES parts(part_number),
    UNIQUE(part_number, model_number)
);

-- Repairs table - troubleshooting guides
CREATE TABLE IF NOT EXISTS repairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appliance_type TEXT NOT NULL, -- 'refrigerator' or 'dishwasher'
    symptom TEXT NOT NULL,
    description TEXT,
    difficulty TEXT,
    percentage_reported TEXT,
    parts_needed TEXT, -- comma-separated part names
    symptom_detail_url TEXT,
    repair_video_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Blogs table - educational content
CREATE TABLE IF NOT EXISTS blogs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    excerpt TEXT,
    author TEXT,
    date_published TEXT,
    category TEXT,
    tags TEXT, -- JSON string
    content TEXT,
    image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Part categories for better organization
CREATE TABLE IF NOT EXISTS part_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT UNIQUE NOT NULL,
    appliance_type TEXT NOT NULL,
    description TEXT
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_parts_number ON parts(part_number);
CREATE INDEX IF NOT EXISTS idx_parts_brand ON parts(brand);
CREATE INDEX IF NOT EXISTS idx_parts_category ON parts(category);
CREATE INDEX IF NOT EXISTS idx_parts_name ON parts(name);
CREATE INDEX IF NOT EXISTS idx_parts_price ON parts(price);

CREATE INDEX IF NOT EXISTS idx_compatibility_part ON part_compatibility(part_number);
CREATE INDEX IF NOT EXISTS idx_compatibility_model ON part_compatibility(model_number);
CREATE INDEX IF NOT EXISTS idx_compatibility_appliance ON part_compatibility(appliance_type);

CREATE INDEX IF NOT EXISTS idx_repairs_appliance ON repairs(appliance_type);
CREATE INDEX IF NOT EXISTS idx_repairs_symptom ON repairs(symptom);
CREATE INDEX IF NOT EXISTS idx_repairs_difficulty ON repairs(difficulty);

CREATE INDEX IF NOT EXISTS idx_blogs_title ON blogs(title);
CREATE INDEX IF NOT EXISTS idx_blogs_category ON blogs(category);
CREATE INDEX IF NOT EXISTS idx_blogs_url ON blogs(url);

-- Full-text search indexes for better search capabilities
CREATE VIRTUAL TABLE IF NOT EXISTS parts_fts USING fts5(
    part_number,
    name,
    description,
    brand,
    category,
    content='parts',
    content_rowid='id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS repairs_fts USING fts5(
    symptom,
    description,
    parts_needed,
    appliance_type,
    content='repairs',
    content_rowid='id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS blogs_fts USING fts5(
    title,
    content,
    category,
    author,
    content='blogs',
    content_rowid='id'
);

-- Triggers to keep FTS tables in sync
CREATE TRIGGER IF NOT EXISTS parts_fts_insert AFTER INSERT ON parts BEGIN
    INSERT INTO parts_fts(rowid, part_number, name, description, brand, category)
    VALUES (new.id, new.part_number, new.name, new.description, new.brand, new.category);
END;

CREATE TRIGGER IF NOT EXISTS parts_fts_update AFTER UPDATE ON parts BEGIN
    UPDATE parts_fts SET 
        part_number = new.part_number,
        name = new.name,
        description = new.description,
        brand = new.brand,
        category = new.category
    WHERE rowid = new.id;
END;

CREATE TRIGGER IF NOT EXISTS parts_fts_delete AFTER DELETE ON parts BEGIN
    DELETE FROM parts_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS repairs_fts_insert AFTER INSERT ON repairs BEGIN
    INSERT INTO repairs_fts(rowid, symptom, description, parts_needed, appliance_type)
    VALUES (new.id, new.symptom, new.description, new.parts_needed, new.appliance_type);
END;

CREATE TRIGGER IF NOT EXISTS repairs_fts_update AFTER UPDATE ON repairs BEGIN
    UPDATE repairs_fts SET 
        symptom = new.symptom,
        description = new.description,
        parts_needed = new.parts_needed,
        appliance_type = new.appliance_type
    WHERE rowid = new.id;
END;

CREATE TRIGGER IF NOT EXISTS repairs_fts_delete AFTER DELETE ON repairs BEGIN
    DELETE FROM repairs_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS blogs_fts_insert AFTER INSERT ON blogs BEGIN
    INSERT INTO blogs_fts(rowid, title, content, category, author)
    VALUES (new.id, new.title, new.content, new.category, new.author);
END;

CREATE TRIGGER IF NOT EXISTS blogs_fts_update AFTER UPDATE ON blogs BEGIN
    UPDATE blogs_fts SET 
        title = new.title,
        content = new.content,
        category = new.category,
        author = new.author
    WHERE rowid = new.id;
END;

CREATE TRIGGER IF NOT EXISTS blogs_fts_delete AFTER DELETE ON blogs BEGIN
    DELETE FROM blogs_fts WHERE rowid = old.id;
END;

-- Insert some initial categories
INSERT OR IGNORE INTO part_categories (category_name, appliance_type, description) VALUES
('Water Filters', 'refrigerator', 'Water filtration systems and replacement filters'),
('Door Seals', 'refrigerator', 'Door gaskets and sealing components'),
('Compressor Parts', 'refrigerator', 'Compressor and related cooling system components'),
('Shelves & Drawers', 'refrigerator', 'Interior storage components'),
('Ice Makers', 'refrigerator', 'Ice making system components'),
('Wash Arms', 'dishwasher', 'Spray arms and water distribution components'),
('Pumps', 'dishwasher', 'Water circulation and drainage pumps'),
('Filters', 'dishwasher', 'Water and debris filtering components'),
('Door Components', 'dishwasher', 'Door latches, seals, and related parts'),
('Control Systems', 'dishwasher', 'Electronic controls and user interfaces');
