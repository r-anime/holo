PRAGMA foreign_keys=OFF;

CREATE TABLE IF NOT EXISTS "ShowsNew" (
			id		INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
			name		TEXT NOT NULL,
			name_en		TEXT,
			length		INTEGER,
			type		INTEGER NOT NULL,
			has_source	INTEGER NOT NULL DEFAULT 0,
			enabled		INTEGER NOT NULL DEFAULT 1,
			delayed		INTEGER NOT NULL DEFAULT 0,
			is_nsfw		INTEGER NOT NULL DEFAULT 0,
			FOREIGN KEY(type) REFERENCES ShowTypes(id)
		);

INSERT INTO ShowsNew (id, name, length, type, has_source, enabled, delayed, type)
	SELECT * FROM Shows;

DROP TABLE Shows;

ALTER TABLE ShowsNew RENAME TO Shows;

PRAGMA foreign_keys=ON;
