# Find Next Tune

## Project Setup

**Step 1 Create a virtual environment**

```
python -m venv .venv
```

**Step 2 Activate the virtual environment:**

```powershell
.venv\Scripts\Activate
```

COnfirm `(.venv)` at start prompt.

**Step 3: Install dependencies:**

```powershell
pip install -r requirements.txt
```

**Step 4: Set up environment variables:**

Create a `.env` file in the project root directory by copying the example file:

```powershell
copy .env.example .env
```

Then edit the `.env` file and add your actual API keys:

```env
# Django Secret Key
DJANGO_SECRET_KEY=your-django-secret-key-here

# Spotify API Configuration
# Get these from https://developer.spotify.com/dashboard
SPOTIFY_CLIENT_ID=your-spotify-client-id
SPOTIFY_CLIENT_SECRET=your-spotify-client-secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/spotify/callback/

# Last.fm API Configuration
# Get this from https://www.last.fm/api/account/create
LASTFM_API_KEY=your-lastfm-api-key

# Debug Mode (True for development, False for production)
DEBUG=True
```

**Step 5: Make and run database migrations**

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py makemigrations api
python manage.py migrate --database=api
```

**Step 6: Run the Server**

```powershell
python manage.py runserver
```
