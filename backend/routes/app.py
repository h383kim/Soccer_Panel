from fastapi import FastAPI, HTTPException, Form, Query, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None


@app.get("/")
async def home():
    connection = get_db_connection()
    if connection and connection.is_connected():
        return {"message": "Welcome to CS348~~ Connected to Database."}
    else:
        return {"message": "Welcome to CS348~~"}

########## User Authentication Feature #################
##### Sign Up endpoint
@app.post("/signup")
async def signup(username: str = Form(...), password: str = Form(...), email: str = Form(...)):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Users WHERE username = %s", (username,))
    user_exist = cursor.fetchone() is not None

    if user_exist:
        raise HTTPException(status_code=401, detail="Username already exists.")

    cursor.execute("INSERT INTO Users(username, password, email, role_id)  \
                   VALUES (%s, %s, %s, 2);", (username, password, email))
    db.commit()

    cursor.close()
    db.close()
    return JSONResponse(content={"message": "User registered successfully. Please log in."}, status_code=201)

##### Log In endpoint
@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Users WHERE username = %s AND password = %s", (username, password))
    account = cursor.fetchone()
    cursor.close()
    db.close()

    if account:
        return {"message": "Login successful!", "id": account['user_id']}
    else:
        raise HTTPException(status_code=400, detail="Incorrect username or password.")

@app.post("/logout")
async def logout():
    return {"message": "Logout successful."}

##### Recent Games by league_id endpoints
@app.get("/recentgames")
async def recent_games(league: str = None, page: int = 1, page_size: int = 10):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    query = ("""SELECT Matches.match_id, Matches.date, Matches.match_location,
                       Matches.league_id, Leagues.leaguename, 
                       Matches.hometeam_id, Matches.awayteam_id,
                       home.teamname as home_team, away.teamname as away_team, 
                       Matches.hometeam_score, Matches.awayteam_score
                FROM Matches 
                LEFT JOIN Leagues ON Matches.league_id = Leagues.league_id
                LEFT JOIN Teams as home on Matches.hometeam_id = home.team_id 
                LEFT JOIN Teams as away on Matches.awayteam_id = away.team_id """)
    offset = (page - 1) * page_size
    if league and league != 'all':
        query += "WHERE Leagues.league_id = %s "
        query += "ORDER BY Matches.date DESC LIMIT %s OFFSET %s"
        cursor.execute(query, (league, page_size, offset))
    else:
        query += "ORDER BY Matches.date DESC LIMIT %s OFFSET %s"
        cursor.execute(query, (page_size, offset))

    games = cursor.fetchall()
    cursor.close()
    db.close()
    return games

########## Search Feature #################
##### Search player endpoint
# Search for player by name, team, position & nationality
@app.get("/player")
async def search_player(
    name: str = None, 
    team: str = None, 
    position: str = None, 
    nationality: int = None,
    page: int = 1,
    page_size: int = 10
):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    query = """SELECT player_id, playername, teamname, position, countryname as nationality, age
               FROM Players 
               LEFT JOIN Teams ON Players.team_id = Teams.team_id
               LEFT JOIN Country ON Players.player_nationality_id = Country.country_id
               WHERE 1 = 1
            """
    params = []
    
    if name:
        # If search term is short, fallback to LIKE search
        if len(name) < 4:
            query += " AND LOWER(playername) LIKE %s"
            params.append(f"%{name.lower()}%")
        else:
            query += " AND MATCH(playername) AGAINST(%s IN NATURAL LANGUAGE MODE)"
            params.append(name)
    
    if team:
        query += " AND Players.team_id = %s"
        params.append(team)

    if position:
        query += " AND LOWER(position) LIKE %s"
        params.append(f"%{position.lower()}%")

    if nationality is not None:
        query += " AND Players.player_nationality_id = %s"
        params.append(nationality)
    
    offset = (page - 1) * page_size
    query += " ORDER BY playername LIMIT %s OFFSET %s"
    params.append(page_size)
    params.append(offset)

    cursor.execute(query, params)
    results = cursor.fetchall()

    cursor.close()
    db.close()

    if not results:
        return JSONResponse(content={"message": "No players found", "results": []}, status_code=200)

    return results

##### Search game endpoint
# Search game between start_date and end_date by league
# start_date and end_date in form "yyyy-mm-dd"
@app.get("/game")
async def search_game(start_date: str = None, end_date: str = None, league: int = None, page: int = 1, page_size: int = 10):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    query = """SELECT Matches.match_id, Matches.date, Matches.match_location,
                Matches.league_id, Leagues.leaguename, 
                Matches.hometeam_id, Matches.awayteam_id,
                home.teamname as home_team, away.teamname as away_team, 
                Matches.hometeam_score, Matches.awayteam_score
                FROM Matches 
                LEFT JOIN Leagues ON Matches.league_id = Leagues.league_id
                LEFT JOIN Teams as home on Matches.hometeam_id = home.team_id
                LEFT JOIN Teams as away on Matches.awayteam_id = away.team_id
                WHERE 1 = 1
            """
    params = []
    print(start_date, end_date, league)
    if start_date:
        query += " AND date >=  %s"
        params.append(start_date)
    
    if end_date:
        query += " AND date <=  %s"
        params.append(end_date)
    
    if league:
        query += " AND Matches.league_id = %s"
        params.append(league)

    query += " ORDER BY date"
    offset = (page - 1) * page_size
    query += " LIMIT %s OFFSET %s"
    params.append(page_size)
    params.append(offset)

    cursor.execute(query, params)
    results = cursor.fetchall()

    cursor.close()
    db.close()

    if not results:
        raise HTTPException(status_code=404, detail="Game not found.")
    
    return results

########## Favorities Feature #################
##### Add Favorite Player endpoint
# If (user_id, player_id) do not exists in FavoritePlayers, add Favorites
# If (user_id, player_id)  exists in FavoritePlayers, delete Favorites
@app.get("/favorite/player/add")
async def modify_fav_player(userid: str, playerid: str): 
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM FavoritePlayers WHERE user_id = %s and player_id = %s ", (userid, playerid))
    favorite_exist = cursor.fetchone() is not None

    message = ""
    
    # If favorite exist, delete favorite
    if favorite_exist:
        cursor.execute("DELETE FROM FavoritePlayers  \
                        WHERE user_id = %s and player_id = %s;", (userid, playerid))
        message = "Favorite Player removed successfully"
    else: 
        cursor.execute("INSERT INTO FavoritePlayers(user_id, player_id)  \
                        VALUES (%s, %s);", (userid, playerid))
        message = "Favorite Player added successfully"
    db.commit()

    cursor.close()
    db.close()
    return JSONResponse(content={"message": message}, status_code=201)

##### View Favorite Player endpoint
@app.get("/favorite/player/view")
async def view_fav_player(userid: str): 
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    query = ("""SELECT f.user_id, f.player_id, p.playername, t.teamname, p.position, f.dateAdded 
             FROM FavoritePlayers f
             LEFT JOIN Players p 
             ON f.player_id = p.player_id
             LEFT JOIN Teams t
             ON p.team_id = t.team_id
             WHERE user_id = %s 
             ORDER BY dateAdded DESC""")
    
    cursor.execute(query, (userid,))

    favorites = cursor.fetchall()
    cursor.close()
    db.close()
    return favorites

##### Add Favorite Team endpoint
# If (user_id, team_id) do not exists in FavoriteTeams, add Favorites
# If (user_id, team_id)  exists in FavoriteTeams, delete Favorites
@app.get("/favorite/team/add")
async def modify_fav_team(userid: str, teamid: str): 
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM FavoriteTeams WHERE user_id = %s and team_id = %s ", (userid, teamid))
    favorite_exist = cursor.fetchone() is not None

    message = ""
    
    # If favorite exist, delete favorite
    if favorite_exist:
        cursor.execute("DELETE FROM FavoriteTeams \
                        WHERE user_id = %s and team_id = %s;", (userid, teamid))
        message = "Favorite Team removed successfully"
    else: 
        cursor.execute("INSERT INTO FavoriteTeams(user_id, team_id)  \
                        VALUES (%s, %s);", (userid, teamid))
        message = "Favorite Team added successfully"
    db.commit()

    cursor.close()
    db.close()
    return JSONResponse(content={"message": message}, status_code=201)

##### View Favorite Team endpoint
@app.get("/favorite/team/view")
async def view_fav_team(userid: str): 
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    query = ("""SELECT f.user_id, f.team_id, t.teamname, l.leaguename, c.countryname, f.dateAdded
             FROM FavoriteTeams f
             LEFT JOIN Teams t
             on f.team_id = t.team_id
             LEFT JOIN Leagues l
             on t.league_id = l.league_id
             LEFT JOIN Country c
             on l.league_nationality_id = c.country_id
             WHERE user_id = %s 
             ORDER BY dateAdded DESC""")
    
    cursor.execute(query, (userid,))

    favorites = cursor.fetchall()
    cursor.close()
    db.close()
    return favorites

############ TEAM Statistics ###############
##### Players by team_id
@app.get("/teams/players")
async def get_team_player(team: str = None):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    query = ("SELECT * FROM Players ")
    if team and team != 'all':
        query += "WHERE team_id = %s"
        cursor.execute(query, (team,))
    else:
        cursor.execute(query)

    players = cursor.fetchall()
    cursor.close()
    db.close()
    return players

##### Number of match win/lose/draw by team
@app.get("/teams/stats")
async def get_teams_stat(team: str = None):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    query = ("""WITH match_status as (
            SELECT Matches.match_id, 
                    CASE WHEN (hometeam_score = awayteam_score) THEN 1 
                        ELSE 0 END AS draw, 
                    CASE WHEN (hometeam_score > awayteam_score) THEN hometeam_id \
                        WHEN (hometeam_score < awayteam_score) THEN awayteam_id \
                        ELSE hometeam_id END AS win_team, \
                    CASE WHEN (hometeam_score > awayteam_score) THEN awayteam_id \
                        WHEN (hometeam_score < awayteam_score) THEN hometeam_id \
                        ELSE awayteam_id END AS lose_team \
            FROM Matches
            ), 

            team_win as (
            SELECT Teams.team_id, count(match_status.match_id) as win
            FROM Teams
            LEFT JOIN match_status on Teams.team_id = match_status.win_team and match_status.draw = 0
            GROUP BY Teams.team_id
            ),

            team_lose as (
            SELECT Teams.team_id, count(match_status.match_id) as lose
            FROM Teams
            LEFT JOIN match_status on Teams.team_id = match_status.lose_team and match_status.draw = 0
            GROUP BY Teams.team_id
            ), 

            team_draw as (
            SELECT Teams.team_id, count(a.match_id) + count(b.match_id)  as draw
            FROM Teams
            LEFT JOIN match_status as a on Teams.team_id = a.win_team and a.draw = 1
            LEFT JOIN match_status as b on Teams.team_id = b.lose_team and b.draw = 1
            GROUP BY Teams.team_id
            )
             
            SELECT Teams.team_id, Teams.teamname, Teams.league_id, team_win.win, team_lose.lose, team_draw.draw
            FROM Teams
            LEFT JOIN team_win on Teams.team_id = team_win.team_id
            LEFT JOIN team_lose on Teams.team_id = team_lose.team_id
            LEFT JOIN team_draw on Teams.team_id = team_draw.team_id
            WHERE Teams.team_id = %s
            """)
    cursor.execute(query, (team, ))
    stats = cursor.fetchall()
    cursor.close()
    db.close()
    return stats

##### Players & Number of match win/lose/draw by team
@app.get("/teams/details")
async def get_team_details(team: str = None):
    if not team:
        raise HTTPException(status_code=400, detail="Team ID must be provided.")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Fetch team statistics with league name
    stats_query = ("""WITH match_status as (
            SELECT Matches.match_id, 
                   CASE WHEN (hometeam_score = awayteam_score) THEN 1 
                        ELSE 0 END AS draw, 
                   CASE WHEN (hometeam_score > awayteam_score) THEN hometeam_id 
                        WHEN (hometeam_score < awayteam_score) THEN awayteam_id 
                        ELSE hometeam_id END AS win_team, 
                   CASE WHEN (hometeam_score > awayteam_score) THEN awayteam_id 
                        WHEN (hometeam_score < awayteam_score) THEN hometeam_id 
                        ELSE awayteam_id END AS lose_team 
            FROM Matches
            ), 

            team_win as (
            SELECT Teams.team_id, count(match_status.match_id) as win
            FROM Teams
            LEFT JOIN match_status on Teams.team_id = match_status.win_team and match_status.draw = 0
            WHERE Teams.team_id = %s
            GROUP BY Teams.team_id
            ),

            team_lose as (
            SELECT Teams.team_id, count(match_status.match_id) as lose
            FROM Teams
            LEFT JOIN match_status on Teams.team_id = match_status.lose_team and match_status.draw = 0
            WHERE Teams.team_id = %s
            GROUP BY Teams.team_id
            ), 

            team_draw as (
            SELECT Teams.team_id, count(a.match_id) + count(b.match_id) as draw
            FROM Teams
            LEFT JOIN match_status as a on Teams.team_id = a.win_team and a.draw = 1
            LEFT JOIN match_status as b on Teams.team_id = b.lose_team and b.draw = 1
            WHERE Teams.team_id = %s
            GROUP BY Teams.team_id
            )

            SELECT Teams.team_id, Teams.teamname, Leagues.leaguename, 
                   IFNULL(team_win.win, 0) as win, 
                   IFNULL(team_lose.lose, 0) as lose, 
                   IFNULL(team_draw.draw, 0) as draw
            FROM Teams
            LEFT JOIN team_win on Teams.team_id = team_win.team_id
            LEFT JOIN team_lose on Teams.team_id = team_lose.team_id
            LEFT JOIN team_draw on Teams.team_id = team_draw.team_id
            LEFT JOIN Leagues on Teams.league_id = Leagues.league_id
            WHERE Teams.team_id = %s
            """)
    cursor.execute(stats_query, (team, team, team, team))
    stats = cursor.fetchone()

    # Fetch team players
    players_query = "SELECT * FROM Players WHERE team_id = %s"
    cursor.execute(players_query, (team,))
    players = cursor.fetchall()

    cursor.close()
    db.close()

    if not stats:
        raise HTTPException(status_code=404, detail="Team not found.")

    return {
        "team_id": stats["team_id"],
        "teamname": stats["teamname"],
        "league_name": stats["leaguename"],
        "statistics": {
            "win": stats["win"],
            "lose": stats["lose"],
            "draw": stats["draw"]
        },
        "players": players
    }

##### Team leaderboard by league
@app.get("/teams/leaderboard")
async def get_league_board(league: str = None):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    query = ("""WITH match_status as (
            SELECT Matches.match_id, 
                    CASE WHEN (hometeam_score = awayteam_score) THEN 1 
                        ELSE 0 END AS draw, 
                    CASE WHEN (hometeam_score > awayteam_score) THEN hometeam_id \
                        WHEN (hometeam_score < awayteam_score) THEN awayteam_id \
                        ELSE hometeam_id END AS win_team, \
                    CASE WHEN (hometeam_score > awayteam_score) THEN awayteam_id \
                        WHEN (hometeam_score < awayteam_score) THEN hometeam_id \
                        ELSE awayteam_id END AS lose_team \
            FROM Matches
            Where league_id = %s
            ), 
            team_win as (
            SELECT Teams.team_id, count(match_status.match_id) as win
            FROM Teams
            LEFT JOIN match_status on Teams.team_id = match_status.win_team and match_status.draw = 0
            GROUP BY Teams.team_id
            ),
            team_lose as (
            SELECT Teams.team_id, count(match_status.match_id) as lose
            FROM Teams
            LEFT JOIN match_status on Teams.team_id = match_status.lose_team and match_status.draw = 0
            GROUP BY Teams.team_id
            ), 
            team_draw as (
            SELECT Teams.team_id, count(a.match_id) + count(b.match_id)  as draw
            FROM Teams
            LEFT JOIN match_status as a on Teams.team_id = a.win_team and a.draw = 1
            LEFT JOIN match_status as b on Teams.team_id = b.lose_team and b.draw = 1
            GROUP BY Teams.team_id
            ) 
             
            SELECT Teams.team_id, Teams.teamname, Teams.league_id, Leagues.leaguename, 
            IFNULL(team_win.win, 0) + IFNULL(team_lose.lose, 0) + IFNULL(team_draw.draw, 0) as game, 
            IFNULL(team_win.win, 0) as win, 
            IFNULL(team_lose.lose, 0) as lose, 
            IFNULL(team_draw.draw, 0) as draw, 
            IFNULL(team_win.win, 0) * 3 + IFNULL(team_lose.lose, 0) * (-1) + IFNULL(team_draw.draw, 0) * 1 as point
            FROM Teams
            LEFT JOIN team_win on Teams.team_id = team_win.team_id
            LEFT JOIN team_lose on Teams.team_id = team_lose.team_id
            LEFT JOIN team_draw on Teams.team_id = team_draw.team_id
            LEFT JOIN Leagues on Teams.league_id = Leagues.league_id
            WHERE Teams.league_id = %s
            ORDER by point DESC
            """)
    cursor.execute(query, (league, league))
    stats = cursor.fetchall()
    cursor.close()
    db.close()
    return stats

##### Players info
@app.get("/players")
async def get_all_players(page: int = 1, page_size: int = 10):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    offset = (page - 1) * page_size
    query = """SELECT 
                   p.player_id, 
                   p.playername, 
                   p.position, 
                   p.player_nationality_id, 
                   p.age, 
                   t.teamname, 
                   c.countryname AS nationality
               FROM Players p
               LEFT JOIN Teams t ON p.team_id = t.team_id
               LEFT JOIN Country c ON p.player_nationality_id = c.country_id
               LIMIT %s OFFSET %s"""
    cursor.execute(query, (page_size, offset))
    players = cursor.fetchall()

    cursor.close()
    db.close()

    if not players:
        raise HTTPException(status_code=404, detail="No players found.")

    return players

##### Country info
@app.get("/nationality")
async def get_nationality():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Country;")
    nationality = cursor.fetchall()
    return nationality

##### Leagues info 
@app.get("/leagues")
async def get_all_leagues():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Leagues;")
    leagues = cursor.fetchall()
    cursor.close()
    db.close()
    return leagues

############ Top Scorers Ranked ###############
##### Players by team_id
@app.get("/top-scorers-ranked")
async def get_top_scorers_ranked(
    league: str = Query(None, description="League name to filter by"),
    team: str = Query(None, description="Team name to filter by"),
    nationality: str = Query(None, description="Nationality to filter by"),
    limit: int = Query(10, description="Number of top scorers to retrieve")
):
    if sum(param is not None for param in [league, team, nationality]) > 1:
        raise HTTPException(
            status_code=400, 
            detail="Only one of league, team, or nationality filters can be used at a time."
        )

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    base_query = """
        SELECT 
            player_id, playername, teamname, leaguename, nationality, total_goals,
            RANK() OVER (ORDER BY total_goals DESC) AS score_rank
        FROM (
            SELECT 
                p.player_id, p.playername, t.teamname, l.leaguename, c.countryname AS nationality,
                SUM(s.goal) AS total_goals
            FROM Statistics s
            INNER JOIN Players p ON s.player_id = p.player_id
            INNER JOIN Teams t ON p.team_id = t.team_id
            INNER JOIN Leagues l ON t.league_id = l.league_id
            LEFT JOIN Country c ON p.player_nationality_id = c.country_id
            WHERE 1=1
    """

    params = []
    # Adding filters dynamizcally based on user input
    if league:
        base_query += " AND LOWER(l.leaguename) LIKE %s"
        params.append(f"%{league.lower()}%")
    elif team:
        base_query += " AND LOWER(t.teamname) LIKE %s"
        params.append(f"%{team.lower()}%")
    elif nationality:
        base_query += " AND LOWER(c.countryname) LIKE %s"
        params.append(f"%{nationality.lower()}%")
    
    # Complete the query: group by the same columns used in SELECT
    base_query += """
            GROUP BY p.player_id, p.playername, t.teamname, l.leaguename, nationality
        ) AS GoalsSubquery
        ORDER BY score_rank ASC, playername ASC
        LIMIT %s
    """

    # Finally, add the limit
    params.append(limit)

    cursor.execute(base_query, params)
    ranked_scorers = cursor.fetchall()
    
    cursor.close()
    db.close()

    if not ranked_scorers:
        return JSONResponse(content={"message": "No top scorers found."}, status_code=200)

    return ranked_scorers

############ Notifications ###############
@app.get("/notifications/{user_id}")
async def get_notifications(user_id: int):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT notification_id, message, created_at
        FROM Notifications
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 20
    """, (user_id,))
    notifications = cursor.fetchall()
    cursor.close()
    db.close()

    return notifications

## advanced feature R11, player form tracker
# Player form tracker endpoint
@app.get("/players/form_tracker")
async def player_form_tracker(player_id: int):
    """
    Endpoint to track a player's recent performance.
    Returns two JSON lists:
      - form_tracker: Contains the rolling average of goals over the last 5 matches along with goals,
                      pass accuracy, assists, and playtime.
      - games: List of all games that this player played in along with goals, pass accuracy, assists, and playtime.
    """
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    # Query 1: Get rolling average performance data with additional stats
    form_tracker_query = """
    SELECT 
        s.player_id, 
        p.playername, 
        m.date, 
        s.goal,
        s.pass_acc,
        s.assist,
        s.playtime,
        AVG(s.goal) OVER (
            PARTITION BY s.player_id 
            ORDER BY m.date 
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        ) AS rolling_goal_avg
    FROM Statistics s
    JOIN Matches m ON s.match_id = m.match_id
    JOIN Players p ON s.player_id = p.player_id
    WHERE s.player_id = %s
    ORDER BY m.date ASC;
    """
    cursor.execute(form_tracker_query, (player_id,))
    form_tracker_data = cursor.fetchall()
    
    # Query 2: Get details for all games the player participated in including performance stats
    all_games_query = """
    SELECT 
        m.match_id,
        m.date,
        m.match_location,
        m.league_id,
        home.teamname AS home_team,
        away.teamname AS away_team,
        m.hometeam_score,
        m.awayteam_score,
        s.goal,
        s.pass_acc,
        s.assist,
        s.playtime
    FROM Matches m
    JOIN Statistics s ON m.match_id = s.match_id
    LEFT JOIN Teams home ON m.hometeam_id = home.team_id
    LEFT JOIN Teams away ON m.awayteam_id = away.team_id
    WHERE s.player_id = %s
    ORDER BY m.date ASC;
    """
    cursor.execute(all_games_query, (player_id,))
    all_games_data = cursor.fetchall()
    
    cursor.close()
    db.close()
    
    if not form_tracker_data:
        raise HTTPException(status_code=404, detail="No data found for player performance.")
    
    return {
        "form_tracker": form_tracker_data,
        "games": all_games_data
    }

@app.get("/league/standings")
async def get_league_standings(league: int):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    query = """
    WITH match_status AS (
        SELECT 
            match_id,
            hometeam_id,
            awayteam_id,
            CASE 
                WHEN hometeam_score = awayteam_score THEN 'draw'
                WHEN hometeam_score > awayteam_score THEN 'home_win'
                ELSE 'away_win' 
            END AS result
        FROM Matches
        WHERE league_id = %s
    ),
    home_results AS (
        SELECT hometeam_id AS team_id,
               COUNT(CASE WHEN hometeam_score > awayteam_score THEN 1 END) AS win,
               COUNT(CASE WHEN hometeam_score < awayteam_score THEN 1 END) AS lose,
               COUNT(CASE WHEN hometeam_score = awayteam_score THEN 1 END) AS draw
        FROM Matches
        WHERE league_id = %s
        GROUP BY hometeam_id
    ),
    away_results AS (
        SELECT awayteam_id AS team_id,
               COUNT(CASE WHEN awayteam_score > hometeam_score THEN 1 END) AS win,
               COUNT(CASE WHEN awayteam_score < hometeam_score THEN 1 END) AS lose,
               COUNT(CASE WHEN awayteam_score = hometeam_score THEN 1 END) AS draw
        FROM Matches
        WHERE league_id = %s
        GROUP BY awayteam_id
    ),
    team_results AS (
        SELECT team_id,
               SUM(win) AS win,
               SUM(lose) AS lose,
               SUM(draw) AS draw
        FROM (
            SELECT * FROM home_results
            UNION ALL
            SELECT * FROM away_results
        ) AS combined
        GROUP BY team_id
    )
    SELECT 
        t.team_id,
        t.teamname,
        l.leaguename,
        IFNULL(tr.win, 0) AS win,
        IFNULL(tr.lose, 0) AS lose,
        IFNULL(tr.draw, 0) AS draw,
        (IFNULL(tr.win, 0) * 3 + IFNULL(tr.draw, 0)) AS points,
        RANK() OVER (ORDER BY (IFNULL(tr.win, 0) * 3 + IFNULL(tr.draw, 0)) DESC) AS ranking
    FROM Teams t
    JOIN Leagues l ON t.league_id = l.league_id
    LEFT JOIN team_results tr ON t.team_id = tr.team_id
    WHERE t.league_id = %s
    ORDER BY points DESC, win DESC, draw DESC;
    """
    # We need to supply 'league' four times for the placeholders above.
    cursor.execute(query, (league, league, league, league))
    standings = cursor.fetchall()
    cursor.close()
    db.close()
    return standings

if __name__ == '__main__':
    uvicorn.run(app, port=5001)
