PRAGMA foreign_keys = ON;

INSERT INTO well_mode_history(well_id, mode, date_from, date_to, note)
SELECT w.id, w.type, '1970-01-01', NULL, 'initial from design type'
FROM wells w
WHERE NOT EXISTS (SELECT 1 FROM well_mode_history h WHERE h.well_id = w.id);
