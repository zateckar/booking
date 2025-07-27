from pydantic import BaseModel

class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str


class UserPassword(BaseModel):
    password: str


class User(UserBase):
    id: int
    is_admin: bool
    parking_lots: list["ParkingLotSimple"] = []

    class Config:
        from_attributes = True


class ParkingSpaceBase(BaseModel):
    space_number: str
    position_x: int
    position_y: int
    width: int
    height: int
    color: str

class ParkingSpaceCreate(ParkingSpaceBase):
    pass

class ParkingSpaceUpdate(BaseModel):
    space_number: str | None = None
    position_x: int | None = None
    position_y: int | None = None
    width: int | None = None
    height: int | None = None
    color: str | None = None


class ParkingSpaceBulkUpdate(ParkingSpaceUpdate):
    id: int


class ParkingSpace(ParkingSpaceBase):
    id: int
    lot_id: int
    parking_lot: "ParkingLotSimple"

    class Config:
        from_attributes = True


class ParkingLotBase(BaseModel):
    name: str
    image: str | None = None

class ParkingLotCreate(ParkingLotBase):
    pass

class ParkingLot(ParkingLotBase):
    id: int
    spaces: list[ParkingSpace] = []

    class Config:
        from_attributes = True


class ParkingLotSimple(ParkingLotBase):
    id: int

    class Config:
        from_attributes = True


from datetime import datetime, timezone
from pydantic import field_validator, model_validator
from typing import Self, Any

class BookingBase(BaseModel):
    space_id: int
    start_time: datetime
    end_time: datetime
    license_plate: str

    @field_validator('start_time', 'end_time')
    @classmethod
    def validate_timezone_aware(cls, v: datetime) -> datetime:
        """Ensure datetime is timezone-aware, default to UTC if naive"""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    @field_validator('license_plate')
    @classmethod
    def validate_license_plate(cls, v: str) -> str:
        """Validate and normalize license plate format"""
        if not v or not v.strip():
            raise ValueError('License plate cannot be empty')
        # Remove extra whitespace and convert to uppercase
        normalized = v.strip().upper()
        if len(normalized) < 2 or len(normalized) > 10:
            raise ValueError('License plate must be between 2 and 10 characters')
        return normalized

    @model_validator(mode='after')
    def validate_time_range(self) -> Self:
        """Validate that start_time is before end_time"""
        if self.start_time >= self.end_time:
            raise ValueError('Start time must be before end time')
        return self


class BookingCreate(BookingBase):
    """Schema for creating new bookings with additional validation rules"""
    
    @model_validator(mode='after')
    def validate_booking_constraints(self) -> Self:
        """Validate booking constraints for new bookings only"""
        # Check minimum booking duration (15 minutes)
        duration = self.end_time - self.start_time
        if duration.total_seconds() < 900:  # 15 minutes
            raise ValueError('Booking duration must be at least 15 minutes')
        
        # Check maximum booking duration (24 hours)
        if duration.total_seconds() > 86400:  # 24 hours
            raise ValueError('Booking duration cannot exceed 24 hours')
        
        # Ensure booking is not too far in the past (allow 5 minutes grace period)
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        grace_period = now - timedelta(minutes=5)
        
        if self.start_time < grace_period:
            raise ValueError('Cannot create bookings more than 5 minutes in the past')
        
        return self

class BookingUpdate(BaseModel):
    start_time: datetime | None = None
    end_time: datetime | None = None
    license_plate: str | None = None

    @field_validator('start_time', 'end_time')
    @classmethod
    def validate_timezone_aware(cls, v: datetime | None) -> datetime | None:
        """Ensure datetime is timezone-aware, default to UTC if naive"""
        if v is None:
            return v
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    @field_validator('license_plate')
    @classmethod
    def validate_license_plate(cls, v: str | None) -> str | None:
        """Validate and normalize license plate format"""
        if v is None:
            return v
        if not v or not v.strip():
            raise ValueError('License plate cannot be empty')
        # Remove extra whitespace and convert to uppercase
        normalized = v.strip().upper()
        if len(normalized) < 2 or len(normalized) > 10:
            raise ValueError('License plate must be between 2 and 10 characters')
        return normalized

# Base class for retrieving bookings without time validation
class BookingRead(BaseModel):
    id: int
    space_id: int | None
    start_time: datetime
    end_time: datetime
    license_plate: str
    user: User
    space: ParkingSpace | None
    is_cancelled: bool
    deleted_space_info: str | None = None
    
    @field_validator('start_time', 'end_time')
    @classmethod
    def validate_timezone_aware(cls, v: datetime) -> datetime:
        """Ensure datetime is timezone-aware, default to UTC if naive"""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
    
    # Disable validation for response models
    model_config = {
        "from_attributes": True,
        "validate_default": False,
    }

# Keep the original Booking class for backward compatibility
class Booking(BookingRead):
    # Explicitly disable time validation for response models
    model_config = {
        "from_attributes": True,
        "validate_default": False,
    }
    
    # Override the validate_time_range method to disable validation
    @model_validator(mode='after')
    def validate_time_range(self) -> Self:
        """Disable time validation for response models"""
        return self


class BookingAdmin(BaseModel):
    """Enhanced booking schema for admin interface with all related data"""
    id: int
    space_id: int | None
    user_id: int | None
    start_time: datetime
    end_time: datetime
    license_plate: str
    is_cancelled: bool
    deleted_space_info: str | None = None
    created_at: datetime
    updated_at: datetime
    user: User | None = None
    space: ParkingSpace | None = None
    
    @field_validator('start_time', 'end_time', 'created_at', 'updated_at')
    @classmethod
    def validate_timezone_aware(cls, v: datetime) -> datetime:
        """Ensure datetime is timezone-aware, default to UTC if naive"""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
    
    model_config = {
        "from_attributes": True,
        "validate_default": False,
    }


class AvailabilityResponse(BaseModel):
    booked_space_ids: list[int]
    space_license_plates: dict[int, str] = {}


class OIDCProviderBase(BaseModel):
    issuer: str
    display_name: str  # User-friendly name for login button
    client_id: str
    client_secret: str
    well_known_url: str
    scopes: str = "openid email profile"


class OIDCProviderCreate(OIDCProviderBase):
    pass


class OIDCProviderUpdate(BaseModel):
    issuer: str | None = None
    display_name: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    well_known_url: str | None = None
    scopes: str | None = None


class OIDCProvider(OIDCProviderBase):
    id: int

    class Config:
        from_attributes = True


class EmailSettingsBase(BaseModel):
    sendgrid_api_key: str | None = None
    from_email: str | None = None
    from_name: str = "Parking Booking System"
    booking_confirmation_enabled: bool = True
    reports_enabled: bool = False
    report_recipients: list[str] = []
    report_schedule_hour: int = 9
    report_frequency: str = "daily"
    timezone: str = "UTC"
    # Dynamic reports scheduling
    dynamic_reports_enabled: bool = False
    dynamic_report_recipients: list[str] = []
    dynamic_report_schedule_hour: int = 9
    dynamic_report_frequency: str = "weekly"
    dynamic_report_template_id: int | None = None


class EmailSettingsCreate(EmailSettingsBase):
    pass


class EmailSettingsUpdate(BaseModel):
    sendgrid_api_key: str | None = None
    from_email: str | None = None
    from_name: str | None = None
    booking_confirmation_enabled: bool | None = None
    reports_enabled: bool | None = None
    report_recipients: list[str] | None = None
    report_schedule_hour: int | None = None
    report_frequency: str | None = None
    timezone: str | None = None
    # Dynamic reports scheduling
    dynamic_reports_enabled: bool | None = None
    dynamic_report_recipients: list[str] | None = None
    dynamic_report_schedule_hour: int | None = None
    dynamic_report_frequency: str | None = None
    dynamic_report_template_id: int | None = None


class EmailSettings(EmailSettingsBase):
    id: int
    last_report_sent: datetime | None = None
    last_dynamic_report_sent: datetime | None = None

    class Config:
        from_attributes = True


class ApplicationLogBase(BaseModel):
    level: str
    logger_name: str
    message: str
    module: str | None = None
    function: str | None = None
    line_number: int | None = None
    user_id: int | None = None
    request_id: str | None = None
    extra_data: str | None = None


class ApplicationLog(ApplicationLogBase):
    id: int
    timestamp: datetime
    user: User | None = None

    class Config:
        from_attributes = True


class OIDCClaimMappingBase(BaseModel):
    claim_name: str
    mapped_field_name: str
    mapping_type: str  # "role", "string", "array", "number", "boolean"
    is_required: bool = False
    role_admin_values: list[str] = []  # For role mappings
    default_value: str | None = None
    display_label: str
    description: str | None = None


class OIDCClaimMappingCreate(OIDCClaimMappingBase):
    pass


class OIDCClaimMappingUpdate(BaseModel):
    claim_name: str | None = None
    mapped_field_name: str | None = None
    mapping_type: str | None = None
    is_required: bool | None = None
    role_admin_values: list[str] | None = None
    default_value: str | None = None
    display_label: str | None = None
    description: str | None = None


class OIDCClaimMapping(OIDCClaimMappingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserProfileBase(BaseModel):
    profile_data: dict = {}


class UserProfile(UserProfileBase):
    id: int
    user_id: int
    last_oidc_update: datetime | None = None

    class Config:
        from_attributes = True


class ReportColumnBase(BaseModel):
    column_name: str
    display_label: str
    column_type: str  # "static", "mapped", "calculated"
    data_type: str  # "string", "number", "array", "boolean"
    is_available: bool = True
    sort_order: int = 0


class ReportColumnCreate(ReportColumnBase):
    pass


class ReportColumnUpdate(BaseModel):
    column_name: str | None = None
    display_label: str | None = None
    column_type: str | None = None
    data_type: str | None = None
    is_available: bool | None = None
    sort_order: int | None = None


class ReportColumn(ReportColumnBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ReportTemplateBase(BaseModel):
    name: str
    description: str | None = None
    selected_columns: list[str] = []
    is_default: bool = False


class ReportTemplateCreate(ReportTemplateBase):
    pass


class ReportTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    selected_columns: list[str] | None = None
    is_default: bool | None = None


class ReportTemplate(ReportTemplateBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClaimsDiscoveryRequest(BaseModel):
    sample_token: str


class ClaimsDiscoveryResponse(BaseModel):
    discovered_claims: dict[str, Any]
    existing_mappings: list[OIDCClaimMapping]
    unmapped_claims: list[str]


class DynamicReportRequest(BaseModel):
    selected_columns: list[str]
    months: int = 2
    start_date: datetime | None = None
    end_date: datetime | None = None
    include_excel: bool = False

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_timezone_aware(cls, v: datetime | None) -> datetime | None:
        """Ensure datetime is timezone-aware, default to UTC if naive"""
        if v is None:
            return v
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    @model_validator(mode='after')
    def validate_date_range(self) -> 'DynamicReportRequest':
        """Validate that start_date is before end_date when both are provided"""
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValueError('Start date must be before end date')
        return self


class DynamicReportColumn(BaseModel):
    field: str
    label: str
    type: str  # "static", "mapped", "calculated"
    format: str | None = None  # For special formatting like arrays


class ScheduledDynamicReportBase(BaseModel):
    name: str
    description: str | None = None
    template_id: int
    recipients: list[str] = []
    frequency: str = "weekly"  # "daily", "weekly", "monthly"
    schedule_hour: int = 9
    timezone: str = "UTC"
    is_enabled: bool = True
    include_excel: bool = True
    months_period: int = 2


class ScheduledDynamicReportCreate(ScheduledDynamicReportBase):
    pass


class ScheduledDynamicReportUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    template_id: int | None = None
    recipients: list[str] | None = None
    frequency: str | None = None
    schedule_hour: int | None = None
    timezone: str | None = None
    is_enabled: bool | None = None
    include_excel: bool | None = None
    months_period: int | None = None


class ScheduledDynamicReport(ScheduledDynamicReportBase):
    id: int
    last_sent: datetime | None = None
    last_error: str | None = None
    created_by: int
    created_at: datetime
    updated_at: datetime
    template: ReportTemplate | None = None

    class Config:
        from_attributes = True


class StylingSettingsBase(BaseModel):
    # Logo settings
    logo_path: str | None = None
    logo_alt_text: str = "Company Logo"
    logo_max_height: int = 50
    login_logo_max_height: int = 100
    show_logo_in_navbar: bool = True
    show_logo_on_login: bool = True
    
    # Color theme
    primary_color: str = "#007bff"
    secondary_color: str = "#6c757d"
    success_color: str = "#28a745"
    danger_color: str = "#dc3545"
    warning_color: str = "#ffc107"
    info_color: str = "#17a2b8"
    light_color: str = "#f8f9fa"
    dark_color: str = "#343a40"
    
    # Text and background
    body_bg_color: str = "#ffffff"
    text_color: str = "#212529"
    link_color: str = "#007bff"
    link_hover_color: str = "#0056b3"
    
    # Typography
    font_family: str = "system-ui"
    heading_font_family: str | None = None
    
    # Navigation
    navbar_bg_color: str = "#f8f9fa"
    navbar_text_color: str = "#212529"
    navbar_brand_text: str = "Parking Booking"
    
    # Login page customization
    login_bg_color: str | None = None
    login_card_bg_color: str | None = None
    
    # Custom CSS
    custom_css: str | None = None
    
    # System
    enabled: bool = False


class StylingSettingsCreate(StylingSettingsBase):
    pass


class StylingSettingsUpdate(BaseModel):
    # Logo settings
    logo_path: str | None = None
    logo_alt_text: str | None = None
    logo_max_height: int | None = None
    login_logo_max_height: int | None = None
    show_logo_in_navbar: bool | None = None
    show_logo_on_login: bool | None = None
    
    # Color theme
    primary_color: str | None = None
    secondary_color: str | None = None
    success_color: str | None = None
    danger_color: str | None = None
    warning_color: str | None = None
    info_color: str | None = None
    light_color: str | None = None
    dark_color: str | None = None
    
    # Text and background
    body_bg_color: str | None = None
    text_color: str | None = None
    link_color: str | None = None
    link_hover_color: str | None = None
    
    # Typography
    font_family: str | None = None
    heading_font_family: str | None = None
    
    # Navigation
    navbar_bg_color: str | None = None
    navbar_text_color: str | None = None
    navbar_brand_text: str | None = None
    
    # Login page customization
    login_bg_color: str | None = None
    login_card_bg_color: str | None = None
    
    # Custom CSS
    custom_css: str | None = None
    
    # System
    enabled: bool | None = None


class StylingSettings(StylingSettingsBase):
    id: int

    class Config:
        from_attributes = True
