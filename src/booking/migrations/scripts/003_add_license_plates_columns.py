"""
Add license plates columns to dynamic reports.

This migration adds the license_plates_list column configuration to enable
showing actual license plate values in dynamic reports.
"""

from sqlalchemy import text
from ..base import BaseMigration


class AddLicensePlatesColumnsMigration(BaseMigration):
    """Add license plates columns to dynamic reports."""
    
    version = "003"
    description = "Add license plates columns to dynamic reports"
    
    def up(self) -> None:
        """Add the new license plates column configurations."""
        
        # Check if report_columns table exists
        try:
            self.session.execute(text("SELECT COUNT(*) FROM report_columns LIMIT 1"))
        except Exception:
            print("⚠️  report_columns table does not exist yet - skipping license plates columns migration")
            return
        
        # Check if license_plates_list column already exists
        existing_check = self.session.execute(text(
            "SELECT COUNT(*) FROM report_columns WHERE column_name = 'license_plates_list'"
        )).scalar()
        
        if existing_check > 0:
            print("✅ License plates list column already exists - skipping")
            return
        
        # Insert the license_plates_list column configuration
        insert_sql = text("""
        INSERT INTO report_columns (column_name, display_label, column_type, data_type, is_available, sort_order)
        VALUES (:column_name, :display_label, :column_type, :data_type, :is_available, :sort_order)
        """)
        
        # Add license_plates_list column
        self.session.execute(insert_sql, {
            'column_name': 'license_plates_list',
            'display_label': 'License Plates Used',
            'column_type': 'static',
            'data_type': 'array',
            'is_available': True,
            'sort_order': 105  # Put after other standard columns
        })
        
        # Also ensure the count column exists with better labeling
        count_check = self.session.execute(text(
            "SELECT COUNT(*) FROM report_columns WHERE column_name = 'license_plates_count'"
        )).scalar()
        
        if count_check == 0:
            self.session.execute(insert_sql, {
                'column_name': 'license_plates_count',
                'display_label': 'Number of License Plates',
                'column_type': 'static',
                'data_type': 'number',
                'is_available': True,
                'sort_order': 104
            })
        
        # Update existing 'license_plates' column to have better labeling for backward compatibility
        update_sql = text("""
        UPDATE report_columns 
        SET display_label = :display_label, sort_order = :sort_order
        WHERE column_name = :column_name
        """)
        
        self.session.execute(update_sql, {
            'column_name': 'license_plates',
            'display_label': 'License Plates Count (Legacy)',
            'sort_order': 103
        })
        
        self.session.commit()
        print("✅ Added license plates columns to dynamic reports")
    
    def down(self) -> None:
        """Remove the license plates column configurations."""
        
        # Remove the new columns
        delete_sql = text("DELETE FROM report_columns WHERE column_name IN (:col1, :col2)")
        self.session.execute(delete_sql, {
            'col1': 'license_plates_list',
            'col2': 'license_plates_count'
        })
        
        # Restore original license_plates column labeling
        update_sql = text("""
        UPDATE report_columns 
        SET display_label = :display_label, sort_order = :sort_order
        WHERE column_name = :column_name
        """)
        
        self.session.execute(update_sql, {
            'column_name': 'license_plates',
            'display_label': 'License Plates',
            'sort_order': 0
        })
        
        self.session.commit()
        print("✅ Removed license plates columns from dynamic reports")
    
    def validate(self) -> bool:
        """Validate that the migration can be applied."""
        try:
            # Check if we can access the report_columns table
            self.session.execute(text("SELECT COUNT(*) FROM report_columns LIMIT 1"))
            return True
        except Exception:
            # Table doesn't exist yet, that's fine
            return True
