"""Alerts API endpoints - Price drop notifications and alerts management"""

from typing import List, Optional
from datetime import datetime
from enum import Enum
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc

from core.database import get_db
from core.config import settings
from models.app import App, PriceHistory

router = APIRouter()


# --- Enums and Models ---

class AlertType(str, Enum):
    PRICE_DROP = "price_drop"
    GOES_FREE = "goes_free"
    TARGET_PRICE = "target_price"
    ANY_DISCOUNT = "any_discount"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    TRIGGERED = "triggered"
    PAUSED = "paused"
    EXPIRED = "expired"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    PUSH = "push"
    WEBHOOK = "webhook"


# --- Pydantic Models ---

class PriceAlertCreate(BaseModel):
    app_id: str
    alert_type: AlertType
    target_price: Optional[float] = None  # Required for TARGET_PRICE type
    channels: List[NotificationChannel] = [NotificationChannel.EMAIL]
    email: Optional[EmailStr] = None  # Required if EMAIL in channels


class PriceAlertResponse(BaseModel):
    id: str
    app_id: str
    app_name: str
    alert_type: str
    target_price: Optional[float]
    current_price: float
    status: str
    channels: List[str]
    created_at: str
    triggered_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class AlertHistoryResponse(BaseModel):
    id: str
    alert_id: str
    app_id: str
    app_name: str
    old_price: float
    new_price: float
    change_percentage: float
    triggered_at: str
    notification_sent: bool


class NotificationPayload(BaseModel):
    alert_id: str
    app_id: str
    app_name: str
    app_icon: str
    old_price: float
    new_price: float
    change_percentage: float
    message: str


# --- In-Memory Storage (Replace with database in production) ---
_alerts = {}  # alert_id -> alert data
_alert_history = []  # List of triggered alerts
_user_alerts = {}  # user_id -> list of alert_ids
_id_counter = 0


def _generate_id():
    global _id_counter
    _id_counter += 1
    return f"alert_{_id_counter}"


# --- Helper Functions ---

async def _check_price_drop(
    app_id: str,
    db: AsyncSession
) -> Optional[dict]:
    """Check if an app has dropped in price"""
    # Get current app data
    result = await db.execute(select(App).where(App.id == app_id))
    app = result.scalar_one_or_none()
    
    if not app:
        return None
    
    # Get price history
    result = await db.execute(
        select(PriceHistory)
        .where(PriceHistory.app_id == app_id)
        .order_by(desc(PriceHistory.recorded_at))
        .limit(2)
    )
    history = result.scalars().all()
    
    if len(history) < 2:
        return None
    
    latest = history[0]
    previous = history[1]
    
    # Check if price dropped
    if latest.new_price < previous.new_price:
        change_pct = ((previous.new_price - latest.new_price) / previous.new_price) * 100
        return {
            "app_id": app_id,
            "app_name": app.name,
            "app_icon": app.icon_url,
            "old_price": previous.new_price,
            "new_price": latest.new_price,
            "change_percentage": round(change_pct, 2),
            "is_free": latest.new_price == 0 and previous.new_price > 0
        }
    
    return None


async def _send_notification(
    payload: NotificationPayload,
    channels: List[str],
    email: Optional[str] = None
):
    """Send notification through specified channels"""
    # In production, integrate with:
    # - Email: Resend, SendGrid, AWS SES
    # - Push: Firebase Cloud Messaging, OneSignal
    # - Webhook: User-provided endpoints
    
    for channel in channels:
        if channel == "email" and email:
            # TODO: Integrate with email service (Resend, SendGrid)
            print(f"[EMAIL] Would send to {email}: {payload.message}")
        elif channel == "push":
            # TODO: Integrate with push notification service
            print(f"[PUSH] Would send: {payload.message}")
        elif channel == "webhook":
            # TODO: Call user webhook
            print(f"[WEBHOOK] Would POST: {payload.dict()}")


# --- Alert Management Endpoints ---

@router.post("/price", response_model=PriceAlertResponse, status_code=status.HTTP_201_CREATED)
async def create_price_alert(
    alert_data: PriceAlertCreate,
    background_tasks: BackgroundTasks,
    user_id: str = "user_1",  # TODO: Get from auth token
    db: AsyncSession = Depends(get_db)
):
    """Create a new price alert for an app"""
    
    # Verify app exists
    result = await db.execute(select(App).where(App.id == alert_data.app_id))
    app = result.scalar_one_or_none()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )
    
    # Validate alert type specific requirements
    if alert_data.alert_type == AlertType.TARGET_PRICE and alert_data.target_price is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_price is required for TARGET_PRICE alerts"
        )
    
    if NotificationChannel.EMAIL in alert_data.channels and not alert_data.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email is required when EMAIL channel is selected"
        )
    
    alert_id = _generate_id()
    alert = {
        "id": alert_id,
        "user_id": user_id,
        "app_id": alert_data.app_id,
        "app_name": app.name,
        "alert_type": alert_data.alert_type.value,
        "target_price": alert_data.target_price,
        "current_price": app.price,
        "status": AlertStatus.ACTIVE.value,
        "channels": [c.value for c in alert_data.channels],
        "email": alert_data.email,
        "created_at": datetime.utcnow().isoformat(),
        "triggered_at": None
    }
    
    _alerts[alert_id] = alert
    
    if user_id not in _user_alerts:
        _user_alerts[user_id] = []
    _user_alerts[user_id].append(alert_id)
    
    return PriceAlertResponse(**alert)


@router.get("/price", response_model=List[PriceAlertResponse])
async def get_user_alerts(
    status: Optional[AlertStatus] = None,
    user_id: str = "user_1",  # TODO: Get from auth token
):
    """Get all price alerts for the current user"""
    alert_ids = _user_alerts.get(user_id, [])
    alerts = [_alerts[aid] for aid in alert_ids]
    
    if status:
        alerts = [a for a in alerts if a["status"] == status.value]
    
    return [PriceAlertResponse(**a) for a in alerts]


@router.get("/price/active", response_model=List[PriceAlertResponse])
async def get_active_alerts(user_id: str = "user_1"):
    """Get all active (non-triggered) alerts"""
    alert_ids = _user_alerts.get(user_id, [])
    alerts = [
        _alerts[aid] for aid in alert_ids 
        if _alerts[aid]["status"] == AlertStatus.ACTIVE.value
    ]
    return [PriceAlertResponse(**a) for a in alerts]


@router.delete("/price/{alert_id}")
async def delete_alert(
    alert_id: str,
    user_id: str = "user_1"  # TODO: Get from auth token
):
    """Delete a price alert"""
    if alert_id not in _alerts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    alert = _alerts[alert_id]
    if alert["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this alert"
        )
    
    del _alerts[alert_id]
    _user_alerts[user_id] = [aid for aid in _user_alerts.get(user_id, []) if aid != alert_id]
    
    return {"message": "Alert deleted successfully"}


@router.post("/price/{alert_id}/pause")
async def pause_alert(
    alert_id: str,
    user_id: str = "user_1"
):
    """Pause an active alert"""
    if alert_id not in _alerts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    alert = _alerts[alert_id]
    if alert["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    if alert["status"] != AlertStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only pause active alerts"
        )
    
    alert["status"] = AlertStatus.PAUSED.value
    return {"message": "Alert paused"}


@router.post("/price/{alert_id}/resume")
async def resume_alert(
    alert_id: str,
    user_id: str = "user_1"
):
    """Resume a paused alert"""
    if alert_id not in _alerts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    alert = _alerts[alert_id]
    if alert["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    if alert["status"] != AlertStatus.PAUSED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only resume paused alerts"
        )
    
    alert["status"] = AlertStatus.ACTIVE.value
    return {"message": "Alert resumed"}


# --- Alert Processing & History ---

@router.post("/check", status_code=status.HTTP_200_OK)
async def check_all_alerts(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Check all active alerts and trigger notifications.
    This would typically be called by a scheduled job.
    """
    triggered = []
    
    for alert_id, alert in _alerts.items():
        if alert["status"] != AlertStatus.ACTIVE.value:
            continue
        
        # Check price drop
        drop_info = await _check_price_drop(alert["app_id"], db)
        
        if not drop_info:
            continue
        
        should_trigger = False
        message = ""
        
        # Check alert type conditions
        if alert["alert_type"] == AlertType.GOES_FREE.value and drop_info["is_free"]:
            should_trigger = True
            message = f"🎉 {drop_info['app_name']} is now FREE! (was ${drop_info['old_price']})"
        
        elif alert["alert_type"] == AlertType.PRICE_DROP.value:
            should_trigger = True
            message = f"📉 Price drop! {drop_info['app_name']} dropped from ${drop_info['old_price']} to ${drop_info['new_price']} ({drop_info['change_percentage']}% off)"
        
        elif alert["alert_type"] == AlertType.TARGET_PRICE.value:
            if drop_info["new_price"] <= alert.get("target_price", 0):
                should_trigger = True
                message = f"🎯 Target price reached! {drop_info['app_name']} is now ${drop_info['new_price']} (target was ${alert['target_price']})"
        
        elif alert["alert_type"] == AlertType.ANY_DISCOUNT.value and drop_info["change_percentage"] > 0:
            should_trigger = True
            message = f"💰 Discount alert! {drop_info['app_name']} is {drop_info['change_percentage']}% off"
        
        if should_trigger:
            # Update alert status
            alert["status"] = AlertStatus.TRIGGERED.value
            alert["triggered_at"] = datetime.utcnow().isoformat()
            
            # Create notification payload
            payload = NotificationPayload(
                alert_id=alert_id,
                app_id=drop_info["app_id"],
                app_name=drop_info["app_name"],
                app_icon=drop_info["app_icon"],
                old_price=drop_info["old_price"],
                new_price=drop_info["new_price"],
                change_percentage=drop_info["change_percentage"],
                message=message
            )
            
            # Send notification
            await _send_notification(payload, alert["channels"], alert.get("email"))
            
            # Record in history
            history_entry = {
                "id": f"hist_{len(_alert_history) + 1}",
                "alert_id": alert_id,
                "app_id": drop_info["app_id"],
                "app_name": drop_info["app_name"],
                "old_price": drop_info["old_price"],
                "new_price": drop_info["new_price"],
                "change_percentage": drop_info["change_percentage"],
                "triggered_at": datetime.utcnow().isoformat(),
                "notification_sent": True
            }
            _alert_history.append(history_entry)
            triggered.append(history_entry)
    
    return {
        "checked": len([a for a in _alerts.values() if a["status"] == AlertStatus.ACTIVE.value]),
        "triggered": len(triggered),
        "alerts": triggered
    }


@router.get("/history", response_model=List[AlertHistoryResponse])
async def get_alert_history(
    user_id: str = "user_1",
    limit: int = 50
):
    """Get history of triggered alerts for the user"""
    # Get user's alert IDs
    user_alert_ids = set(_user_alerts.get(user_id, []))
    
    # Filter history
    user_history = [
        h for h in _alert_history 
        if h["alert_id"] in user_alert_ids
    ]
    
    # Sort by triggered_at desc and limit
    user_history.sort(key=lambda x: x["triggered_at"], reverse=True)
    user_history = user_history[:limit]
    
    return [AlertHistoryResponse(**h) for h in user_history]


# --- Bulk Operations ---

@router.post("/bulk/create")
async def create_bulk_alerts(
    app_ids: List[str],
    alert_type: AlertType,
    channels: List[NotificationChannel] = [NotificationChannel.EMAIL],
    email: Optional[EmailStr] = None,
    user_id: str = "user_1",
    db: AsyncSession = Depends(get_db)
):
    """Create the same alert for multiple apps"""
    created = []
    
    for app_id in app_ids:
        try:
            alert_data = PriceAlertCreate(
                app_id=app_id,
                alert_type=alert_type,
                channels=channels,
                email=email
            )
            # Reuse create logic
            result = await create_price_alert(alert_data, None, user_id, db)
            created.append(result)
        except HTTPException:
            # Skip apps that don't exist
            continue
    
    return {
        "created": len(created),
        "alerts": created
    }


@router.delete("/bulk/clear")
async def clear_all_alerts(
    status: Optional[AlertStatus] = None,
    user_id: str = "user_1"
):
    """Clear all alerts (optionally filtered by status)"""
    alert_ids = _user_alerts.get(user_id, [])
    removed = 0
    
    for alert_id in alert_ids[:]:
        alert = _alerts.get(alert_id)
        if alert and (not status or alert["status"] == status.value):
            del _alerts[alert_id]
            removed += 1
    
    _user_alerts[user_id] = [aid for aid in alert_ids if aid in _alerts]
    
    return {"removed": removed}
