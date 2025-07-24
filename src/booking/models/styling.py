from sqlalchemy import Boolean, Column, Integer, String, Text
from .base import BaseModel


class StylingSettings(BaseModel):
    __tablename__ = "styling_settings"

    # Logo settings
    logo_path = Column(String)  # Path to uploaded logo file
    logo_alt_text = Column(String, default="Company Logo")
    logo_max_height = Column(Integer, default=50)  # Max height in pixels for navbar
    login_logo_max_height = Column(Integer, default=100)  # Max height in pixels for login page
    show_logo_in_navbar = Column(Boolean, default=True)
    show_logo_on_login = Column(Boolean, default=True)
    
    # Color theme
    primary_color = Column(String, default="#007bff")  # Bootstrap primary
    secondary_color = Column(String, default="#6c757d")  # Bootstrap secondary
    success_color = Column(String, default="#28a745")  # Bootstrap success
    danger_color = Column(String, default="#dc3545")  # Bootstrap danger
    warning_color = Column(String, default="#ffc107")  # Bootstrap warning
    info_color = Column(String, default="#17a2b8")  # Bootstrap info
    light_color = Column(String, default="#f8f9fa")  # Bootstrap light
    dark_color = Column(String, default="#343a40")  # Bootstrap dark
    
    # Text and background
    body_bg_color = Column(String, default="#ffffff")
    text_color = Column(String, default="#212529")
    link_color = Column(String, default="#007bff")
    link_hover_color = Column(String, default="#0056b3")
    
    # Typography
    font_family = Column(String, default="system-ui")  # Default system font
    heading_font_family = Column(String)  # Optional separate heading font
    
    # Navigation
    navbar_bg_color = Column(String, default="#f8f9fa")
    navbar_text_color = Column(String, default="#212529")
    navbar_brand_text = Column(String, default="Parking Booking")
    
    # Login page customization
    login_bg_color = Column(String)  # Optional login background color
    login_card_bg_color = Column(String)  # Optional login card background
    
    # Custom CSS
    custom_css = Column(Text)  # Allow custom CSS overrides
    
    # System
    enabled = Column(Boolean, default=False)  # Enable custom styling
