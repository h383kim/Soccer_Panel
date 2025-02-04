CREATE DATABASE IF NOT EXISTS soccer_app;
USE soccer_app;

DROP TABLE IF EXISTS FAVORITE_TEAM;
DROP TABLE IF EXISTS GAME;
DROP TABLE IF EXISTS PLAYER;
DROP TABLE IF EXISTS TEAM;
DROP TABLE IF EXISTS LEAGUE;
DROP TABLE IF EXISTS COUNTRY;
DROP TABLE IF EXISTS APP_USER;

CREATE TABLE COUNTRY (
     id INT PRIMARY KEY,
     name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE LEAGUE (
    id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    country_id INT NOT NULL,
    level INT DEFAULT 1,
    FOREIGN KEY (country_id) REFERENCES COUNTRY(id)
);

CREATE TABLE TEAM (
                      id INT PRIMARY KEY,
                      name VARCHAR(100) NOT NULL,
                      league_id INT NOT NULL,
                      logo VARCHAR(255) NULL,
                      ranking INT DEFAULT NULL,
                      wins INT DEFAULT 0,
                      draws INT DEFAULT 0,
                      losses INT DEFAULT 0,
                      FOREIGN KEY (league_id) REFERENCES LEAGUE(id)
);


CREATE TABLE PLAYER (
                        id INT PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        country_id INT NOT NULL,
                        team_id INT NULL,
                        height DECIMAL(4,1) NULL,
                        weight DECIMAL(5,2) NULL,
                        age INT NULL,
                        number INT NULL,
                        position ENUM('GK', 'DEF', 'MID', 'FWD') NOT NULL,
                        FOREIGN KEY (country_id) REFERENCES COUNTRY(id),
                        FOREIGN KEY (team_id) REFERENCES TEAM(id)
);


CREATE TABLE GAME (
                      id INT PRIMARY KEY,
                      home_team_id INT NOT NULL,
                      away_team_id INT NOT NULL,
                      home_team_score INT DEFAULT 0,
                      away_team_score INT DEFAULT 0,
                      date DATE NOT NULL,
                      FOREIGN KEY (home_team_id) REFERENCES TEAM(id),
                      FOREIGN KEY (away_team_id) REFERENCES TEAM(id)
);


CREATE TABLE APP_USER (
                          id INT PRIMARY KEY,
                          username VARCHAR(50) NOT NULL UNIQUE,
                          password VARCHAR(255) NOT NULL,
                          role ENUM('admin', 'user') DEFAULT 'user' NOT NULL
);

CREATE TABLE FAVORITE_TEAM (
                               user_id INT NOT NULL,
                               team_id INT NOT NULL,
                               added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                               PRIMARY KEY (user_id, team_id),
                               FOREIGN KEY (user_id) REFERENCES APP_USER(id) ON DELETE CASCADE,
                               FOREIGN KEY (team_id) REFERENCES TEAM(id) ON DELETE CASCADE
);