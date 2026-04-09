import os

# Application Configuration
class Config:
    """Base configuration class"""
    
    # Secret key for session management (change this in production)
    SECRET_KEY = 'your-secret-key-here-change-this-in-production'
    
    # Database configuration
    DATABASE_PATH = 'database/students.db'
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload and export settings
    UPLOAD_FOLDER = 'data/uploads'
    EXPORT_FOLDER = 'data/exports'
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Model settings
    MODEL_PATH = 'models/student_performance_model.pkl'
    
    # Pagination settings
    ITEMS_PER_PAGE = 20
    
    # Chart colors
    COLORS = {
        'primary': '#2E86AB',
        'secondary': '#A23B72',
        'success': '#3AAE5C',
        'warning': '#F18F01',
        'danger': '#C73E1D',
        'info': '#5D9B9B',
        'A+': '#2E86AB',
        'A': '#3AAE5C',
        'B': '#5D9B9B',
        'C': '#F18F01',
        'D': '#C73E1D',
        'F': '#A23B72'
    }
    
    # Grade thresholds
    GRADE_THRESHOLDS = {
        'A+': 90,
        'A': 80,
        'B': 70,
        'C': 60,
        'D': 50,
        'F': 0
    }
    
    # Feature columns for ML model
    FEATURE_COLUMNS = [
        'study_hours', 'previous_score', 'attendance_percentage',
        'parent_income', 'sleep_hours', 'age', 'midterm_score',
        'assignment_score', 'quiz_score', 'project_score'
    ]
    
    # Categorical columns for encoding
    CATEGORICAL_COLUMNS = [
        'gender', 'parent_education_level', 'internet_access_at_home',
        'extracurricular_activities', 'tuition_classes', 
        'library_access', 'transport_facility'
    ]
    
    # Target column
    TARGET_COLUMN = 'final_score'


# Create necessary folders if they don't exist
def setup_folders():
    """Create required folders"""
    folders = [
        Config.UPLOAD_FOLDER,
        Config.EXPORT_FOLDER,
        'database',
        'models',
        'static/assets',
        'data/raw',
        'data/processed'
    ]
    
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
    
    print("✅ All required folders created!")


# Demo user credentials (for testing)
DEMO_USERS = {
    'admin': {
        'password': 'admin123',
        'role': 'admin',
        'name': 'Administrator'
    },
    'teacher': {
        'password': 'teacher123',
        'role': 'teacher',
        'name': 'Teacher User'
    },
    'viewer': {
        'password': 'viewer123',
        'role': 'viewer',
        'name': 'Viewer User'
    }
}