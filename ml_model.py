import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')

class StudentPerformanceModel:
    """Machine Learning model for predicting student performance"""
    
    def __init__(self, data_path='data/processed/student_data_cleaned.csv'):
        """Initialize the ML model"""
        self.data_path = data_path
        self.df = None
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_columns = None
        self.load_data()
    
    def load_data(self):
        """Load the student data"""
        self.df = pd.read_csv(self.data_path)
        print(f"✅ Data loaded: {len(self.df)} records")
        return self.df
    
    def preprocess_data(self):
        """Preprocess data for machine learning"""
        # Create a copy
        df_processed = self.df.copy()
        
        # Encode categorical variables
        categorical_cols = ['gender', 'parent_education_level', 'internet_access_at_home',
                           'extracurricular_activities', 'tuition_classes', 
                           'library_access', 'transport_facility']
        
        for col in categorical_cols:
            le = LabelEncoder()
            df_processed[col] = le.fit_transform(df_processed[col])
            self.label_encoders[col] = le
        
        # Define features for prediction
        self.feature_columns = ['study_hours', 'previous_score', 'attendance_percentage',
                                'parent_income', 'sleep_hours', 'age', 'midterm_score',
                                'assignment_score', 'quiz_score', 'project_score']
        
        # Add encoded categorical features
        for col in categorical_cols:
            self.feature_columns.append(col)
        
        # Prepare X and y
        X = df_processed[self.feature_columns]
        y = df_processed['final_score']
        
        return X, y
    
    def train_models(self):
        """Train multiple models and select the best"""
        X, y = self.preprocess_data()
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Define models
        models = {
            'Linear Regression': LinearRegression(),
            'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42),
            'Gradient Boosting': GradientBoostingRegressor(n_estimators=100, random_state=42)
        }
        
        results = {}
        best_model = None
        best_score = -np.inf
        
        print("\n" + "="*60)
        print("TRAINING MODELS")
        print("="*60)
        
        for name, model in models.items():
            # Train model
            model.fit(X_train_scaled, y_train)
            
            # Make predictions
            y_pred = model.predict(X_test_scaled)
            
            # Calculate metrics
            mae = mean_absolute_error(y_test, y_pred)
            mse = mean_squared_error(y_test, y_pred)
            rmse = np.sqrt(mse)
            r2 = r2_score(y_test, y_pred)
            
            # Cross-validation
            cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='r2')
            
            results[name] = {
                'model': model,
                'MAE': mae,
                'MSE': mse,
                'RMSE': rmse,
                'R2': r2,
                'CV_Mean': cv_scores.mean(),
                'CV_Std': cv_scores.std()
            }
            
            print(f"\n📊 {name}:")
            print(f"   R² Score: {r2:.4f}")
            print(f"   MAE: {mae:.2f}")
            print(f"   RMSE: {rmse:.2f}")
            print(f"   CV Score (5-fold): {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
            
            # Track best model
            if r2 > best_score:
                best_score = r2
                best_model = model
                best_model_name = name
        
        print("\n" + "="*60)
        print(f"🏆 BEST MODEL: {best_model_name} (R² = {best_score:.4f})")
        print("="*60)
        
        self.model = best_model
        self.X_test = X_test_scaled
        self.y_test = y_test
        
        return results, best_model_name
    
    def get_feature_importance(self):
        """Get feature importance from the best model"""
        if self.model is None:
            print("❌ Model not trained yet!")
            return None
        
        if hasattr(self.model, 'feature_importances_'):
            importance = self.model.feature_importances_
            features = self.feature_columns
            
            # Sort by importance
            sorted_idx = np.argsort(importance)[::-1]
            
            feature_importance = []
            for i in sorted_idx:
                feature_importance.append({
                    'feature': features[i],
                    'importance': importance[i]
                })
            
            return feature_importance
        else:
            # For Linear Regression, use coefficients
            if hasattr(self.model, 'coef_'):
                importance = np.abs(self.model.coef_)
                features = self.feature_columns
                
                sorted_idx = np.argsort(importance)[::-1]
                
                feature_importance = []
                for i in sorted_idx:
                    feature_importance.append({
                        'feature': features[i],
                        'importance': importance[i]
                    })
                
                return feature_importance
        return None
    
    def predict_performance(self, student_data):
        """Predict performance for a new student"""
        if self.model is None:
            print("❌ Model not trained yet!")
            return None
        
        # Convert input to DataFrame
        if isinstance(student_data, dict):
            student_df = pd.DataFrame([student_data])
        else:
            student_df = student_data
        
        # Encode categorical features
        for col in self.label_encoders:
            if col in student_df.columns:
                student_df[col] = self.label_encoders[col].transform(student_df[col])
        
        # Select features
        X = student_df[self.feature_columns]
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Make prediction
        prediction = self.model.predict(X_scaled)[0]
        
        # Get grade
        if prediction >= 90:
            grade = 'A+'
        elif prediction >= 80:
            grade = 'A'
        elif prediction >= 70:
            grade = 'B'
        elif prediction >= 60:
            grade = 'C'
        elif prediction >= 50:
            grade = 'D'
        else:
            grade = 'F'
        
        return {
            'predicted_score': round(prediction, 2),
            'predicted_grade': grade,
            'confidence': 'High' if self.model.__class__.__name__ != 'LinearRegression' else 'Medium'
        }
    
    def save_model(self, path='models/student_performance_model.pkl'):
        """Save the trained model"""
        if self.model is None:
            print("❌ No model to save!")
            return False
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'label_encoders': self.label_encoders,
            'feature_columns': self.feature_columns
        }
        
        joblib.dump(model_data, path)
        print(f"✅ Model saved to {path}")
        return True
    
    def load_model(self, path='models/student_performance_model.pkl'):
        """Load a trained model"""
        try:
            model_data = joblib.load(path)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.label_encoders = model_data['label_encoders']
            self.feature_columns = model_data['feature_columns']
            print(f"✅ Model loaded from {path}")
            return True
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            # Create a simple fallback model
            print("Creating fallback model...")
            self.model = None
            return False        
    
    def get_model_performance_summary(self):
        """Get summary of model performance"""
        if self.model is None:
            return None
        
        # Make predictions on test set
        y_pred = self.model.predict(self.X_test)
        
        return {
            'r2_score': r2_score(self.y_test, y_pred),
            'mae': mean_absolute_error(self.y_test, y_pred),
            'rmse': np.sqrt(mean_squared_error(self.y_test, y_pred)),
            'model_type': self.model.__class__.__name__
        }

# Create and train the model
if __name__ == "__main__":
    print("\n" + "="*60)
    print("STUDENT PERFORMANCE PREDICTION MODEL")
    print("="*60)
    
    # Initialize model
    ml_model = StudentPerformanceModel()
    
    # Train models
    results, best_model = ml_model.train_models()
    
    # Get feature importance
    print("\n" + "="*60)
    print("FEATURE IMPORTANCE")
    print("="*60)
    
    importance = ml_model.get_feature_importance()
    if importance:
        for i, item in enumerate(importance[:10], 1):
            print(f"{i:2}. {item['feature']:25} : {item['importance']:.4f}")
    
    # Save the model
    ml_model.save_model()
    
    # Test prediction
    print("\n" + "="*60)
    print("SAMPLE PREDICTION")
    print("="*60)
    
    sample_student = {
        'study_hours': 7,
        'previous_score': 85,
        'attendance_percentage': 90,
        'parent_income': 100000,
        'sleep_hours': 7,
        'age': 17,
        'midterm_score': 82,
        'assignment_score': 85,
        'quiz_score': 80,
        'project_score': 88,
        'gender': 'Male',
        'parent_education_level': "Master's",
        'internet_access_at_home': 'Yes',
        'extracurricular_activities': 'Yes',
        'tuition_classes': 'Yes',
        'library_access': 'Yes',
        'transport_facility': 'Yes'
    }
    
    prediction = ml_model.predict_performance(sample_student)
    print(f"\n📈 Predicted Score: {prediction['predicted_score']}")
    print(f"🎓 Predicted Grade: {prediction['predicted_grade']}")
    print(f"📊 Confidence: {prediction['confidence']}")