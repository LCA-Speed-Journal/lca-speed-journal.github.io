# 🏃 LCA Speed Journal: Performance Dashboard

A Streamlit-powered dashboard for tracking athlete progression, leaderboards, and all-time records.  
Data is stored in `/data/sessions` as CSV files and loaded dynamically into the app.

---

## 🚀 Features
- **Home Dashboard** – all-time leaders by metric, gender, and grade groupings
- **Leaderboards** – detailed breakdowns for Max-Velocity, Acceleration, Jumps, and Drills
- **Progression** – weekly charts showing athlete trends across metrics
- **Dynamic Data Loading** – add new CSVs into `/data/sessions/` and they’ll automatically appear in the app

---

## 📂 File Structure
├── Home.py # Main dashboard
├── Leaderboards.py # Leaderboard pages
├── Progression.py # Progression charts
├── utils.py # Shared data loading & helpers
├── requirements.txt # Python dependencies
├── data/
│ └── sessions/ # Drop your CSV data files here

---

## 📊 Data Format
Each CSV in `/data/sessions/` should follow this schema:

| Column         | Example         | Notes                                  |
|----------------|-----------------|----------------------------------------|
| season_phase   | Preseason       | Text phase of training                  |
| week_number    | 5               | Integer                                |
| day_in_week    | 2               | Integer (Mon=1, Tue=2, etc.)           |
| date           | 2023-09-12      | YYYY-MM-DD format                      |
| metric_category| Speed           | Category (e.g., Speed, Jumps)          |
| metric_family  | Acceleration    | Sub-category                           |
| metric_name    | 10m Acceleration| Specific test name                     |
| metric_id      | …               | Optional unique identifier             |
| input_unit     | frames          | Raw measurement unit                   |
| display_unit   | seconds         | Converted display unit                 |
| conversion_formula | …           | Formula if applicable                  |
| athlete_name   | John Doe        | Athlete’s full name                    |
| gender         | Male/Female     | Gender                                 |
| grade          | 9, 10, 11, 12   | Athlete’s grade                        |
| input_value    | 62              | Raw input                              |
| display_value  | 1.82            | Converted display value                |
| attempt_number | 1               | Trial index                            |
| notes          | Good start      | Optional                               |

---

## 🖥️ Running Locally
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/your-repo.git
   cd your-repo
2. Install dependencies
> pip install -r requirements.txt
3. Launch the Streamlit app
> streamlit run Home.py

The app will open in your browser at http://localhost:8501
