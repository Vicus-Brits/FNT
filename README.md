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

**Step 4: Make and run database migrations**

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py makemigrations api
python manage.py migrate --database=api
```

**Step 5: Run the Server**

```powershell
python manage.py runserver
```
