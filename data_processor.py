import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class DataProcessor:
    """Class to handle all data processing and analysis"""
    
    def __init__(self, data_path='data/processed/student_data_cleaned.csv'):
        """Initialize the data processor"""
        self.data_path = data_path
        self.df = None
        self.load_data()
    
    def load_data(self):
        """Load the student data from CSV"""
        try:
            self.df = pd.read_csv(self.data_path)
            print(f"✅ Data loaded successfully: {len(self.df)} records")
            return self.df
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return None
    
    def get_basic_info(self):
        """Get basic information about the dataset"""
        info = {
            'total_students': len(self.df),
            'total_features': len(self.df.columns),
            'memory_usage': float(self.df.memory_usage(deep=True).sum() / 1024 / 1024),
            'missing_values': int(self.df.isnull().sum().sum()),
            'duplicate_rows': int(self.df.duplicated().sum())
        }
        return info
    
    def get_statistical_summary(self):
        """Get statistical summary of numerical columns"""
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        summary = self.df[numeric_cols].describe().to_dict()
        return summary
    
    def get_grade_distribution(self):
        """Get distribution of grades"""
        grade_dist = self.df['grade'].value_counts().to_dict()
        grade_percentages = (self.df['grade'].value_counts(normalize=True) * 100).to_dict()
        return {
            'counts': grade_dist,
            'percentages': grade_percentages
        }
    
    def get_gender_analysis(self):
        """Analyze performance by gender"""
        try:
            analysis = {
                'final_score': {},
                'attendance_percentage': {},
                'study_hours': {}
            }
            for gender in self.df['gender'].unique():
                subset = self.df[self.df['gender'] == gender]
                analysis['final_score'][gender] = {
                    'mean': float(subset['final_score'].mean()),
                    'median': float(subset['final_score'].median()),
                    'std': float(subset['final_score'].std())
                }
                analysis['attendance_percentage'][gender] = {'mean': float(subset['attendance_percentage'].mean())}
                analysis['study_hours'][gender] = {'mean': float(subset['study_hours'].mean())}
            return analysis
        except Exception as e:
            print(f"Error in gender analysis: {e}")
            return {}
    
    def get_parent_education_analysis(self):
        """Analyze impact of parent education on performance"""
        try:
            analysis = {
                'final_score': {},
                'parent_income': {},
                'attendance_percentage': {}
            }
            for edu in self.df['parent_education_level'].unique():
                subset = self.df[self.df['parent_education_level'] == edu]
                analysis['final_score'][edu] = {'mean': float(subset['final_score'].mean())}
                analysis['parent_income'][edu] = {'mean': float(subset['parent_income'].mean())}
                analysis['attendance_percentage'][edu] = {'mean': float(subset['attendance_percentage'].mean())}
            return analysis
        except Exception as e:
            print(f"Error in parent education analysis: {e}")
            return {}
    
    def get_internet_impact(self):
        """Analyze impact of internet access on performance"""
        try:
            analysis = {}
            for internet in self.df['internet_access_at_home'].unique():
                subset = self.df[self.df['internet_access_at_home'] == internet]
                analysis[internet] = {
                    'final_score': {'mean': float(subset['final_score'].mean())},
                    'attendance_percentage': {'mean': float(subset['attendance_percentage'].mean())},
                    'study_hours': {'mean': float(subset['study_hours'].mean())}
                }
            return analysis
        except Exception as e:
            print(f"Error in internet impact analysis: {e}")
            return {}
    
    def get_extracurricular_impact(self):
        """Analyze impact of extracurricular activities"""
        try:
            analysis = {}
            for activity in self.df['extracurricular_activities'].unique():
                subset = self.df[self.df['extracurricular_activities'] == activity]
                analysis[activity] = {
                    'final_score': {'mean': float(subset['final_score'].mean())},
                    'attendance_percentage': {'mean': float(subset['attendance_percentage'].mean())}
                }
            return analysis
        except Exception as e:
            print(f"Error in extracurricular analysis: {e}")
            return {}
    
    def get_correlation_matrix(self):
        """Get correlation between numerical features"""
        numeric_cols = ['study_hours', 'previous_score', 'attendance_percentage',
                       'parent_income', 'sleep_hours', 'midterm_score',
                       'assignment_score', 'quiz_score', 'project_score', 'final_score']
        correlation = self.df[numeric_cols].corr()
        return correlation.to_dict()
    
    def get_top_performers(self, n=10):
        """Get top N performing students"""
        top_students = self.df.nlargest(n, 'final_score')[['name', 'gender', 'final_score', 'grade', 'attendance_percentage', 'study_hours']]
        return top_students.to_dict('records')
    
    def get_bottom_performers(self, n=10):
        """Get bottom N performing students"""
        bottom_students = self.df.nsmallest(n, 'final_score')[['name', 'gender', 'final_score', 'grade', 'attendance_percentage', 'study_hours']]
        return bottom_students.to_dict('records')
    
    def get_study_hours_analysis(self):
        """Analyze study hours vs performance"""
        try:
            # Create study hours brackets
            self.df['study_hours_bracket'] = pd.cut(self.df['study_hours'], 
                                                    bins=[0, 3, 5, 7, 9, 12],
                                                    labels=['Very Low (0-3)', 'Low (3-5)', 'Medium (5-7)', 'High (7-9)', 'Very High (9+)'])
            
            analysis = {}
            for bracket in self.df['study_hours_bracket'].cat.categories:
                subset = self.df[self.df['study_hours_bracket'] == bracket]
                analysis[bracket] = {
                    'final_score': {'mean': float(subset['final_score'].mean()), 'count': len(subset)},
                    'grade': subset['grade'].mode()[0] if len(subset) > 0 else 'N/A'
                }
            return analysis
        except Exception as e:
            print(f"Error in study hours analysis: {e}")
            return {}
    
    def get_attendance_analysis(self):
        """Analyze attendance vs performance"""
        try:
            # Create attendance brackets
            self.df['attendance_bracket'] = pd.cut(self.df['attendance_percentage'],
                                                   bins=[0, 60, 75, 85, 95, 101],
                                                   labels=['Poor (<60%)', 'Below Avg (60-75%)', 'Average (75-85%)', 'Good (85-95%)', 'Excellent (95%+)'])
            
            analysis = {}
            for bracket in self.df['attendance_bracket'].cat.categories:
                subset = self.df[self.df['attendance_bracket'] == bracket]
                analysis[bracket] = {
                    'final_score': {'mean': float(subset['final_score'].mean()), 'count': len(subset)},
                    'grade': subset['grade'].mode()[0] if len(subset) > 0 else 'N/A'
                }
            return analysis
        except Exception as e:
            print(f"Error in attendance analysis: {e}")
            return {}
    
    def get_age_analysis(self):
        """Analyze performance by age"""
        age_stats = self.df.groupby('age').agg({
            'final_score': 'mean',
            'attendance_percentage': 'mean',
            'count': 'size'
        }).round(2)
        return age_stats.to_dict()
    
    def get_insights(self):
        """Generate automated insights from the data"""
        insights = []
        
        # Overall performance insight
        avg_score = self.df['final_score'].mean()
        if avg_score >= 75:
            insights.append("✅ Overall student performance is excellent with average score above 75%")
        elif avg_score >= 60:
            insights.append("📊 Overall student performance is satisfactory with average score above 60%")
        else:
            insights.append("⚠️ Overall student performance needs improvement with average score below 60%")
        
        # Study hours insight
        high_study = self.df[self.df['study_hours'] >= 7]['final_score'].mean()
        low_study = self.df[self.df['study_hours'] < 4]['final_score'].mean()
        if high_study > low_study + 10:
            insights.append("💡 Students who study 7+ hours score 10+ points higher on average")
        
        # Attendance insight
        high_att = self.df[self.df['attendance_percentage'] >= 90]['final_score'].mean()
        low_att = self.df[self.df['attendance_percentage'] < 75]['final_score'].mean()
        if high_att > low_att + 15:
            insights.append("🎯 Attendance above 90% leads to significantly better performance")
        
        # Internet access insight
        internet_score = self.df[self.df['internet_access_at_home'] == 'Yes']['final_score'].mean()
        no_internet_score = self.df[self.df['internet_access_at_home'] == 'No']['final_score'].mean()
        if internet_score > no_internet_score + 5:
            insights.append("🌐 Students with internet access at home perform 5+ points better")
        
        # Parent education insight
        phd_score = self.df[self.df['parent_education_level'] == 'PhD']['final_score'].mean()
        highschool_score = self.df[self.df['parent_education_level'] == 'High School']['final_score'].mean()
        if phd_score > highschool_score + 10:
            insights.append("👨‍👩‍👧 Parent's education level (PhD vs High School) shows 10+ point difference")
        
        # Gender insight
        male_score = self.df[self.df['gender'] == 'Male']['final_score'].mean()
        female_score = self.df[self.df['gender'] == 'Female']['final_score'].mean()
        insights.append(f"👥 Female students average {abs(male_score - female_score):.1f} points {'higher' if female_score > male_score else 'lower'} than male students")
        
        # Grade distribution insight
        grade_counts = self.df['grade'].value_counts()
        if 'A' in grade_counts or 'A+' in grade_counts:
            insights.append("🏆 Top performers (A/A+ grades) demonstrate excellent academic achievement")
        
        return insights
    
    def export_to_excel(self, filename='student_analysis_report.xlsx'):
        """Export analysis to Excel file"""
        import os
        os.makedirs('data/exports', exist_ok=True)
        
        with pd.ExcelWriter(f'data/exports/{filename}') as writer:
            self.df.to_excel(writer, sheet_name='Raw Data', index=False)
            summary = self.df.describe()
            summary.to_excel(writer, sheet_name='Statistical Summary')
            grade_dist = self.df['grade'].value_counts()
            grade_dist.to_excel(writer, sheet_name='Grade Distribution')
            gender_analysis = self.df.groupby('gender')['final_score'].describe()
            gender_analysis.to_excel(writer, sheet_name='Gender Analysis')
            edu_analysis = self.df.groupby('parent_education_level')['final_score'].agg(['mean', 'median', 'count'])
            edu_analysis.to_excel(writer, sheet_name='Parent Education Analysis')
        
        return f'data/exports/{filename}'

# Create an instance for easy import
processor = DataProcessor()

# Test the processor
if __name__ == "__main__":
    print("\n" + "="*50)
    print("DATA PROCESSOR TEST")
    print("="*50)
    
    info = processor.get_basic_info()
    print(f"\n📊 Basic Info: {info}")
    
    insights = processor.get_insights()
    print("\n💡 Key Insights:")
    for insight in insights:
        print(f"   {insight}")
    
    print("\n🏆 Top 5 Performers:")
    top = processor.get_top_performers(5)
    for student in top:
        print(f"   {student['name']}: {student['final_score']} ({student['grade']})")