-- PartSelect Database Exploration Queries
-- Run with: sqlite3 database/partselect.db < database/explore_database.sql

-- Database Summary
.headers on
.mode column

SELECT '=== DATABASE SUMMARY ===' as info;
SELECT 
  'Parts' as table_name, COUNT(*) as record_count FROM parts
UNION ALL
SELECT 'Repairs', COUNT(*) FROM repairs  
UNION ALL
SELECT 'Blogs', COUNT(*) FROM blogs
UNION ALL
SELECT 'Compatibility', COUNT(*) FROM part_compatibility;

-- Brand Distribution
SELECT '=== BRAND DISTRIBUTION ===' as info;
SELECT brand, COUNT(*) as part_count, 
       ROUND(AVG(price), 2) as avg_price,
       MIN(price) as min_price,
       MAX(price) as max_price
FROM parts 
WHERE brand IS NOT NULL 
GROUP BY brand 
ORDER BY part_count DESC 
LIMIT 10;

-- Price Ranges by Category
SELECT '=== PRICE RANGES BY CATEGORY ===' as info;
SELECT category, 
       COUNT(*) as parts_count,
       ROUND(AVG(price), 2) as avg_price,
       ROUND(MIN(price), 2) as min_price, 
       ROUND(MAX(price), 2) as max_price
FROM parts 
WHERE price IS NOT NULL 
GROUP BY category 
ORDER BY avg_price DESC;

-- Ice Maker Related Items
SELECT '=== ICE MAKER PARTS ===' as info;
SELECT part_number, name, brand, price 
FROM parts 
WHERE name LIKE '%ice%' 
ORDER BY price DESC 
LIMIT 10;

-- Repair Guides by Appliance
SELECT '=== REPAIR GUIDES ===' as info;
SELECT appliance_type, symptom, difficulty, 
       CASE WHEN repair_video_url IS NOT NULL THEN 'Yes' ELSE 'No' END as has_video
FROM repairs 
ORDER BY appliance_type, symptom;

-- Most Expensive Parts
SELECT '=== MOST EXPENSIVE PARTS ===' as info;
SELECT part_number, name, brand, price, category
FROM parts 
WHERE price IS NOT NULL 
ORDER BY price DESC 
LIMIT 10;

-- Search for Troubleshooting Keywords
SELECT '=== TROUBLESHOOTING REPAIRS ===' as info;
SELECT appliance_type, symptom, parts_needed, repair_video_url
FROM repairs 
WHERE symptom LIKE '%not%' OR symptom LIKE '%leak%' OR symptom LIKE '%broken%'
ORDER BY appliance_type;

-- Blog Categories
SELECT '=== BLOG CATEGORIES ===' as info;
SELECT category, COUNT(*) as article_count
FROM blogs 
WHERE category IS NOT NULL 
GROUP BY category 
ORDER BY article_count DESC;

-- Full-Text Search Examples
SELECT '=== FTS SEARCH EXAMPLES ===' as info;
SELECT 'Parts matching "water filter":' as search_type;
SELECT part_number, name, brand, price 
FROM parts p
JOIN parts_fts ON parts_fts.rowid = p.id
WHERE parts_fts MATCH 'water filter'
LIMIT 5;

SELECT 'Repairs matching "ice maker":' as search_type;
SELECT appliance_type, symptom, repair_video_url
FROM repairs r
JOIN repairs_fts ON repairs_fts.rowid = r.id  
WHERE repairs_fts MATCH 'ice maker'
LIMIT 3;
