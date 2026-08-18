# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
from fastapi import (
    APIRouter, Depends, 
    HTTPException, 
    Request, BackgroundTasks)
from sqlmodel import Session, desc, asc, select, union_all, update
from haversine import haversine, Unit
from rapidfuzz import fuzz
from dependencies import (
    get_current_user, 
    get_db_session, get_redis_session, 
    get_geoposition_token_data,
)
from core.exceptions import (
    forbidden_exception,
    not_found_exception,
    invalid_request_exception
)
from core.logging import get_request_info
from core.dbmgr import (
    get_redis_chief_locations_key, 
    get_redis_user_locations_key, 
    get_redis_location_last_updates_key,
    get_redis_chief_demotions_key,
    get_redis_spec_locations_key,
    get_redis_spec_location_last_updates_key
)
from models.general import (
    User, UserRole, Alert, AlertOut, 
    AlertType, AlertIn, AlertOutWithInfo, 
    AlertedUser, AlertedUserJoined, AlertedUserJoinedPaginated, 
    GpsCoordinatesSchema, GpsTokenData,
    VotingSchema, ClosingSchema, ClosingType,
    CLOSING_VOTE_POSITIVE, CLOSING_VOTE_NEGATIVE, 
    CLOSING_VOTE_NEUTRAL, CLOSING_VOTE_PUNITIVE,  
    HERO_SCORE_INC_VALUE_TO_ALERT_SENDER,
    HERO_SCORE_INC_VALUE_TO_ALERTED_USERS,
    ExpandingSchema, ALERT_SPREAD_MAX_COUNT,
    MessageIn, Message, MessageOut, ALERT_MAX_MESSAGES_NUM
)
from services.security import (
    now_tz_naive, now_tz_aware
)
from services.alert_btasks import (
    task_alert_search_and_notify,
    task_alert_notify_about_closure,
    task_alert_process_expansion,
    task_alert_notify_on_new_message
)

router = APIRouter(
    tags=["Alerts"]
)

## Alert management endpoints (create, view, vote, close, expand)
    
@router.post("/api/alerts")
def create_alert(alert_in: AlertIn,
            request: Request,
            background_tasks: BackgroundTasks,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session)):
    # Only chiefs can create special type of alerts (managed, general, empty)
    if (alert_in.type != AlertType.local.value):
        if not current_user.is_chief:
            raise forbidden_exception("Only chiefs can create special alerts")
    else:
        if (not current_user.is_reliable) or (current_user.reliability_score <= 0):
            raise forbidden_exception("You are not a reliable user, you can't create local alerts")
    if (alert_in.radius > 1):
        if not current_user.is_chief:
            raise forbidden_exception("Only chiefs can create alerts with radius greater than 1")
    now = now_tz_naive()
    lat_range = 0.2 # 22 km
    long_range = 0.2 # 22 km (approx, at the equator), less at higher latitudes    
    lat_min, lat_max = alert_in.latitude - lat_range, alert_in.latitude + lat_range
    long_min, long_max = alert_in.longitude - long_range, alert_in.longitude + long_range
    recent_alerts = db_session.exec(
        select(Alert).where(
            Alert.created_at > (now - timedelta(hours=1)),
            Alert.latitude > lat_min,
            Alert.latitude < lat_max,
            Alert.longitude > long_min,
            Alert.longitude < long_max,
            Alert.is_closed == False
        )
    ).all()
    for rec_alert in recent_alerts:
        if (alert_in.type == AlertType.general.value) and (rec_alert.type == AlertType.general.value):
            d1 = alert_in.description.lower().strip()
            d2 = rec_alert.description.lower().strip()
            similarity = fuzz.token_set_ratio(d1, d2)
            if similarity >= 90: # similarity threshold (90 means 90%)
                return {"message": "Similar general alert already exists", "similarity": similarity}
        if (alert_in.type != AlertType.general.value) and (rec_alert.type != AlertType.general.value):
            dist = haversine((alert_in.latitude, alert_in.longitude), (rec_alert.latitude, rec_alert.longitude), unit=Unit.KILOMETERS)
            if dist < rec_alert.radius:
                d1 = alert_in.description.lower().strip()
                d2 = rec_alert.description.lower().strip()
                similarity = fuzz.token_set_ratio(d1, d2)
                if similarity >= 50: # similarity threshold (50 means 50%)
                    return {"message": "Similar alert already exists in the area", "similarity": similarity}
    alert = Alert(
        type=alert_in.type,
        description = alert_in.description,
        latitude=alert_in.latitude,
        longitude=alert_in.longitude,
        accuracy = alert_in.accuracy,
        address = alert_in.address,
        radius = alert_in.radius,
        user_id = current_user.id,
        is_pending = True if (alert_in.type != AlertType.general.value) and (alert_in.type != AlertType.empty.value) else False # general and empty alerts are not pending, because we don't have to perform background tasks for this type of alert
    )
    # For local alerts, we adjust the radius proportionally based on the reliability score of the user
    if (alert.type == AlertType.local.value):
        rel_score = current_user.reliability_score 
        alert.radius = min(max(rel_score, 0), 100) / 100 * alert.radius
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    if alert.id is None:
        raise HTTPException(status_code=500, detail="Unknown error creating alert")
    if (alert.type == AlertType.general.value):
        # No need to search for chiefs or users to notify for this type of alert
        return {"message": f"{alert.type.capitalize()} alert created, no need to search for nearby users or chiefs to notify"}
    if (alert.type == AlertType.empty.value):
        # No need to search for chiefs or users to notify for this type of alert
        return {"message": f"{alert.type.capitalize()} alert created, no need to search for nearby users or chiefs to notify"}
    # For managed alerts, we need to search for nearby users and notify them
    # For local alerts, we need to search for the closest chief and nearby users and notify them
    # so... we must go on with the search and notification process, but we do it in background to avoid making the current user wait for it
    alert_copy = Alert.model_validate(alert)
    curr_user_copy = User.model_validate(current_user)
    req_info = get_request_info(str(current_user.id))
    background_tasks.add_task(
        task_alert_search_and_notify, 
        alert_copy, 
        curr_user_copy, 
        request_info=req_info,
        db_engine=request.app.state.db_engine,
        redis_handle=request.app.state.redis_handle
        )
    if alert.type == AlertType.managed.value:
        return {"message": f"{alert.type.capitalize()} alert created, searching for nearby users to notify"}
    else:
        return {"message": f"{alert.type.capitalize()} alert created, searching for nearby users and chiefs to notify"}

@router.get("/api/alerts/recent", response_model=list[AlertOut])
def get_recent_alerts(current_user: User = Depends(get_current_user),
        db_session: Session = Depends(get_db_session)):
    now = now_tz_naive()
    alerts_by_me_stmt = (select(Alert)
        .where(Alert.user_id == current_user.id, Alert.type != AlertType.general.value)
        .where(Alert.created_at > (now - timedelta(days=365))))
    alerts_to_me_stmt = (select(Alert).join(AlertedUser, Alert.id == AlertedUser.alert_id) # type: ignore
        .where(AlertedUser.user_id == current_user.id)
        .where(Alert.created_at > (now - timedelta(days=365))))
    alerts_general_stmt = (select(Alert)
        .where(Alert.type == AlertType.general.value)
        .where(Alert.created_at > (now - timedelta(days=365))))
    statement = union_all(alerts_by_me_stmt, alerts_to_me_stmt, alerts_general_stmt)
    statement = statement.order_by(desc(Alert.created_at))
    alerts = db_session.exec(statement).all() # type: ignore
    for alert in alerts:
        if alert.is_banned:
            alert.description = "[BANNED ALERT]"
    return alerts

@router.get("/api/alerts/{alert_id}", response_model=AlertOutWithInfo)
def get_alert(alert_id: int,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session)):
    # API endpoint used by clients to view general details about an alert, 
    # for example: description, gps location, sender name and reliability score, etc.
    statement = (select(Alert, User)
        .join(User, Alert.user_id == User.id) # type: ignore
        .where(Alert.id == alert_id))   
    result = db_session.exec(statement).first()
    if result:
        alert = result[0]
        sender = result[1]
    else:
        alert = None
        sender = None
    if (not alert) or (not sender):
        raise not_found_exception("Alert not found")
    if alert.is_banned:
        alert.description = "[BANNED ALERT]"
    if current_user.is_chief or current_user.is_admin:
        current_user_has_high_priv = True
    else:
        current_user_has_high_priv = False
    current_user_is_the_sender = False
    current_user_is_alerted = False
    current_user_is_the_manager = False
    current_user_vote = 0
    alerted_manager_id = None
    chief = None
    chief_closing_vote = 0
    alerted_users_num = 0
    votes_up_num = 0
    votes_down_num = 0
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users = db_session.exec(statement).all()
    if current_user.id == alert.user_id:
        current_user_is_the_sender = True
    for au in alerted_users:
        if au.user_id == current_user.id:
            current_user_is_alerted = True
            current_user_vote = au.vote
        if au.is_manager:
            alerted_manager_id = au.user_id
            chief_closing_vote = au.closing_vote
        if au.vote > 0:
            votes_up_num += 1
        elif au.vote < 0:
            votes_down_num += 1
        alerted_users_num += 1
    if alert.type != AlertType.general.value:
        # A note about non-general alerts: 
        # base users can only see alerts they created or alerts they were alerted about;
        # officers can see alerts they created, alerts they were alerted about, and alerts created by users authorized by them;
        if ((not current_user_is_the_sender) and 
                (not current_user.is_admin) and 
                    (not current_user.is_chief)):
            if current_user.is_officer:
                if (not current_user_is_alerted):
                    if sender.authorized_by != current_user.email:
                        raise forbidden_exception()
            else:
                if (not current_user_is_alerted):
                    raise forbidden_exception()
    messages_num = alert.messages_num # for details about database denormalization, see the "messages_num" field in the Alert model
    if alert.type != AlertType.local.value:
        chief = sender
        if current_user_is_the_sender:
            current_user_is_the_manager = True
    else:
        if alerted_manager_id:
            chief = db_session.exec(select(User).where(User.id == alerted_manager_id)).first()
            if current_user.id == alerted_manager_id:
                current_user_is_the_manager = True
    alert_with_info = {
        "alert": alert,
        # We return the complete sender object only 
        # if the caller (current_user) is a chief or an admin, 
        # otherwise we return None for the sender object.
        # In other words: any chief or admin can view personal info about the alert sender
        # (not only the chief alert manager, but any chief or admin)
        "sender": sender if current_user_has_high_priv else None,
        "sender_firstname": sender.firstname,
        "sender_surname": sender.surname,
        "sender_reliability_score": sender.reliability_score,
        "chief_firstname": chief.firstname if chief else None,
        "chief_surname": chief.surname if chief else None,
        "alerted_users_num": alerted_users_num,
        "positive_votes_num": votes_up_num,
        "negative_votes_num": votes_down_num,
        "chief_closing_vote": chief_closing_vote,
        "messages_num": messages_num,
        "user_is_sender": current_user_is_the_sender,
        "user_is_alerted": current_user_is_alerted,
        "user_is_manager": current_user_is_the_manager,
        "user_vote": current_user_vote
    }
    return alert_with_info

@router.get("/api/alerts/{alert_id}/alerted-users", response_model=AlertedUserJoinedPaginated)
def get_alerted_users(alert_id: int,
                role: str | None = None,
                offset: int = 0,
                limit: int = 100,
                current_user: User = Depends(get_current_user), 
                db_session: Session = Depends(get_db_session)):
    # API endpoint used by chiefs to list all alerted users related to a specific alert,
    # so they can see their personal info and their votes about the alert
    # Any chief or admin can see the list of alerted users with their info (not only the chief alert manager)
    if (not current_user.is_admin) and (not current_user.is_chief):
        raise forbidden_exception()
    if offset < 0:
        offset = 0
    if limit not in [10, 100, 1000]:
        limit = 100
    statement = (select(User, AlertedUser)
        .join(AlertedUser, User.id == AlertedUser.user_id) # type: ignore
        .where(AlertedUser.alert_id == alert_id))
    if role:
        statement = statement.where(User.role == role)
    statement = statement.order_by(asc(AlertedUser.distance))
    statement = statement.offset(offset).limit(limit)
    results = db_session.exec(statement).all()
    out_alerted_users = []
    for r in results:
        user = r[0]
        alerted_user = r[1]
        joined_user = AlertedUserJoined(
            user=user,
            alert_id=alert_id,
            distance=alerted_user.distance,
            is_manager=alerted_user.is_manager,
            vote=alerted_user.vote,
            closing_vote=alerted_user.closing_vote
        )
        out_alerted_users.append(joined_user)
    if len(out_alerted_users) == limit:
        next_cursor = offset + limit
    else:
        next_cursor = None
    return {
        "alerted_users": out_alerted_users, 
        "next_cursor": next_cursor
    }

@router.get("/api/alerts/{alert_id}/roles")
def get_alert_roles(alert_id: int,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session)):
    # API endpoint used by chiefs to list all alerted roles related to a specific alert
    if (not current_user.is_admin) and (not current_user.is_chief):
        raise forbidden_exception()
    role_counts = {}
    for role in UserRole:
        role_counts[role.value] = 0
    statement = (select(User, AlertedUser)
            .join(AlertedUser, User.id == AlertedUser.user_id) # type: ignore
            .where(AlertedUser.alert_id == alert_id))
    results = db_session.exec(statement).all()
    for r in results:
        user = r[0]
        if user.role:
            role_counts[user.role] = role_counts.get(user.role, 0) + 1
    return {"alert_roles": [{"role": role, "specialists_count": count} for role, count in role_counts.items()]}

@router.post("/api/alerts/{alert_id}/vote")
def vote_alert(alert_id: int,
            vote_schema: VotingSchema,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session)):
    # API endpoint used by alerted users to vote on an alert. 
    # Upvote (+1) to confirm the alert, downvote (-1) to deny the alert. See VoteSchema model
    vote = vote_schema.vote
    if (not current_user.is_reliable) or (current_user.reliability_score <= 0):
        raise forbidden_exception("You are not a reliable user, you can't vote for this alert")
    # If the current user is not an alerted user for this alert, we can't vote.
    # Also, if the alert is closed, we can't vote anymore.
    statement = (select(AlertedUser, Alert)
        .join(Alert, AlertedUser.alert_id == Alert.id) # type: ignore
        .where(AlertedUser.alert_id == alert_id, AlertedUser.user_id == current_user.id))
    result = db_session.exec(statement).first()
    if not result:
        raise not_found_exception("Alert not found, or you are not an alerted user for this alert")
    alerted_user, alert = result
    if (not alerted_user) or (not alert):
        raise not_found_exception("Alert not found, or you are not an alerted user for this alert")
    if alert.type != AlertType.local.value:
        raise forbidden_exception("You can only vote for local alerts")
    if alert.is_closed:
        raise forbidden_exception("Alert is closed, voting is not allowed anymore")
    if alert.is_expanded:
        raise forbidden_exception("Alert has been expanded by the chief manager, voting is not allowed anymore")
    # If the alerted user (current_user) has already voted about this alert, we can't update the vote
    if alerted_user.vote != 0:
        raise forbidden_exception("You have already voted for this alert, you can't change your vote")
    alerted_user.vote = vote
    db_session.add(alerted_user)
    db_session.commit()
    return {"message": "Vote registered successfully", "vote": vote}

@router.post("/api/alerts/{alert_id}/close")
def close_alert(alert_id: int,
            closing_schema: ClosingSchema,
            request: Request,
            background_tasks: BackgroundTasks,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session)):
    if (not current_user.is_chief):
        raise forbidden_exception("Only chiefs can close alerts")
    alert = db_session.exec(select(Alert).where(Alert.id == alert_id)).first()
    if alert is None:
        raise not_found_exception("Alert not found")
    if alert.is_closed:
        return {"message": "Alert already closed"}
    closing_vote = 0
    if alert.type == AlertType.local.value:
        # Only the chief alert manager can close an alert, not any other chief
        statement = (select(AlertedUser)
            .where(AlertedUser.alert_id == alert.id, AlertedUser.user_id == current_user.id)
            .where(AlertedUser.is_manager == True))
        alerted_user = db_session.exec(statement).first()
        if not alerted_user:
            raise forbidden_exception("Only the chief alert manager can close this alert")
        match closing_schema.type:
            case ClosingType.positive.value:
                closing_vote = CLOSING_VOTE_POSITIVE
            case ClosingType.negative.value:
                closing_vote = CLOSING_VOTE_NEGATIVE
            case ClosingType.neutral.value:
                closing_vote = CLOSING_VOTE_NEUTRAL
            case ClosingType.punitive.value:
                closing_vote = CLOSING_VOTE_PUNITIVE
            case _:
                # This should never happen, because the Pydantic model already validates the closing type 
                # (returning 422 if it's invalid), but we add this check just in case
                raise invalid_request_exception("Invalid closing type")
        alerted_user.closing_vote = closing_vote
        db_session.add(alerted_user)
        sender_stmt = select(User).where(User.id == alert.user_id)
        sender = db_session.exec(sender_stmt).first()
        if not sender:
            raise not_found_exception("Alert sender not found")
        if closing_schema.type != ClosingType.neutral.value:
            alerted_users_stmt = (select(AlertedUser, User)
                    .join(User, User.id == AlertedUser.user_id) # type: ignore
                    .where(AlertedUser.alert_id == alert.id))
            alerted_users_ext = db_session.exec(alerted_users_stmt).all()
            # If the alert is closed in a non-neutral way, 
            # we update the reliability score of the alert sender, according to the closing vote of the chief alert manager. 
            # We increase the hero score of the alert sender if the alert is closed in a positive way.
            # Note: the hero score is similar to the reliability score, but it's only a game mechanic,
            # it's only a way to symbolically reward users that created alerts that were closed in a positive way by the chief alert manager.
            sender.reliability_score += closing_vote
            if sender.reliability_score < 0:
                sender.reliability_score = 0
            elif sender.reliability_score > 100:
                sender.reliability_score = 100
            if closing_schema.type == ClosingType.positive.value:
                sender.hero_score += HERO_SCORE_INC_VALUE_TO_ALERT_SENDER
            elif closing_schema.type == ClosingType.punitive.value:
                sender.hero_score = 0
            db_session.add(sender)
            # We also update the reliability score of all alerted users (except the chief who closed the alert).
            # We increase the reliability score of alerted users that voted in the same way as the chief manager closing type,
            # and we decrease the reliability score of alerted users that voted in the opposite way of the chief manager closing type.
            # We increase the hero score of alerted users that voted in the same way as the chief manager closing type 
            # Note: the hero score is only a game mechanic, it doesn't have any real meaning in the real world,  
            # it's just a way to symbolically reward users that voted in the same way as the chief manager closing type
            for au_ext in alerted_users_ext:
                au = au_ext[0]
                user = au_ext[1]
                if au.user_id != current_user.id: 
                    au_vote = au.vote
                    if au_vote == 0:
                        continue
                    if (au_vote > 0 and closing_vote > 0) or (au_vote < 0 and closing_vote < 0):
                        user.reliability_score += abs(int(closing_vote/2))
                        user.hero_score += HERO_SCORE_INC_VALUE_TO_ALERTED_USERS
                    else:
                        user.reliability_score -= abs(int(closing_vote/2))
                        if closing_schema.type == ClosingType.punitive.value:
                            user.hero_score = 0
                    if user.reliability_score < 0:
                        user.reliability_score = 0
                    elif user.reliability_score > 100:
                        user.reliability_score = 100
                    db_session.add(user)
            if closing_schema.type == ClosingType.punitive.value:
                alert.is_banned = True
                db_session.add(alert)
                upd_stmt = (update(Message)
                        .where(Message.alert_id == alert.id) # type: ignore
                        .where(Message.user_id != current_user.id) # type: ignore
                        .values(is_banned=True)) # type: ignore
                db_session.exec(upd_stmt)
    else:
        # For non-local alerts, the chief alert manager is the chief alert sender,
        # and he is the only one who can close the alert
        if (current_user.id != alert.user_id):
            raise forbidden_exception("Only the chief alert sender (manager) can close this alert")
        if (closing_schema.type != ClosingType.neutral.value):
            raise invalid_request_exception("Non-local alerts can be closed only in a neutral way")
        # For non-local alerts, the closure is always neutral (a normal close),
        # because the alert sender (a chief) is trusted, and alerted users don't vote
        closing_vote = 0
    alert.is_closed = True
    db_session.add(alert)
    db_session.commit()
    if (alert.type == AlertType.local.value) or (alert.type == AlertType.managed.value):
        alert_copy = Alert.model_validate(alert)
        curr_user_copy = User.model_validate(current_user)
        req_info = get_request_info(str(current_user.id))
        background_tasks.add_task(
            task_alert_notify_about_closure,
            alert_copy,
            closing_schema.type, 
            curr_user_copy, 
            request_info=req_info,
            db_engine=request.app.state.db_engine)
    return {
        "message": "Alert closed successfully", 
        "closing_type": closing_schema.type, 
        "closing_vote": closing_vote
    }

@router.post("/api/alerts/{alert_id}/expand")
def expand_alert(alert_id: int,
            request: Request,
            background_tasks: BackgroundTasks,
            expanding_schema: ExpandingSchema,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session)):
    if (not current_user.is_chief):
        raise forbidden_exception("Only chiefs can expand alerts")
    alert = db_session.exec(select(Alert).where(Alert.id == alert_id)).first()
    if not alert:
        raise not_found_exception("Alert not found")
    if alert.is_closed:
        raise forbidden_exception("Alert is closed, it can't be expanded")
    if alert.is_pending:
        raise forbidden_exception("Alert is in pending status, at the moment it can't be expanded")
    if alert.spread_count >= ALERT_SPREAD_MAX_COUNT:
        raise forbidden_exception("Alert has reached the maximum number of expansions")
    if alert.type == AlertType.local.value:
        # Only the chief alert manager can expand a local alert, not any other chief
        statement = (select(AlertedUser)
            .where(AlertedUser.alert_id == alert.id, AlertedUser.user_id == current_user.id)
            .where(AlertedUser.is_manager == True))
        alerted_manager = db_session.exec(statement).first()
        if not alerted_manager:
            raise forbidden_exception("Only the chief alert manager can expand this alert")
    else:
        # For non-local alerts, the chief alert manager is the chief alert sender,
        # and he is the only one who can expand the alert
        if (current_user.id != alert.user_id):
            raise forbidden_exception("Only the chief alert sender (manager) can expand this alert")
        if alert.type == AlertType.general.value:
            raise forbidden_exception("General alerts can't be expanded") 
    alert.is_pending = True
    alert.is_expanded = True
    # If the expansion is not directed to a specific role, 
    # we will increase the radius of the alert
    if (not expanding_schema.role) and (expanding_schema.radius > alert.radius):
        alert.radius = expanding_schema.radius
    # We will increase the spread_count of the alert at the end of background task, 
    # when we will set is_pending to False
    db_session.add(alert)
    db_session.commit()
    alert_copy = Alert.model_validate(alert)
    curr_user_copy = User.model_validate(current_user)
    req_info = get_request_info(str(current_user.id))
    background_tasks.add_task(
        task_alert_process_expansion,
        alert_copy,
        curr_user_copy,
        radius=expanding_schema.radius,
        role=expanding_schema.role,
        request_info=req_info,
        db_engine=request.app.state.db_engine,
        redis_handle=request.app.state.redis_handle)
    return {"message": "Alert expanded successfully"}

## GPS position update endpoint

@router.post("/api/update-gps-position")
async def update_gps_position(
    gps_data: GpsCoordinatesSchema,
    user_data: GpsTokenData = Depends(get_geoposition_token_data),
    redis_client = Depends(get_redis_session)
):
    user_id_str = user_data.user_id # already a string, no need to convert from UUID
    is_chief = user_data.user_is_chief
    user_role = user_data.user_role
    now = now_tz_aware()
    now_int_ts = int(now.timestamp())
    lat, lon = gps_data.latitude, gps_data.longitude
    userloc_key = get_redis_user_locations_key(user_id_str)
    chiefloc_key = get_redis_chief_locations_key(user_id_str)
    last_upd_key = get_redis_location_last_updates_key(user_id_str)
    chief_dem_key = get_redis_chief_demotions_key(user_id_str)
    chief_demoted_at = await redis_client.zscore(chief_dem_key, user_id_str)
    # Potential race condition here if a chief is demoted while updating position,
    # but it's not a big issue because the inconsistency will be temporary (until the next position update)
    # and in the case of an alert, chiefs returned by redis are always checked against the postgres database for safety
    try:
        async with redis_client.pipeline(transaction=True) as pipe:
            if is_chief and (not chief_demoted_at):
                pipe.zrem(userloc_key, user_id_str)
                pipe.geoadd(chiefloc_key, (lon, lat, user_id_str))
            else:
                pipe.zrem(chiefloc_key, user_id_str)
                pipe.geoadd(userloc_key, (lon, lat, user_id_str))
            pipe.zadd(last_upd_key, {user_id_str: now_int_ts})
            if user_role and (user_role in [r.value for r in UserRole]):
                specloc_key = get_redis_spec_locations_key(user_id_str, user_role)
                spec_last_upd_key = get_redis_spec_location_last_updates_key(user_id_str, user_role)
                pipe.geoadd(specloc_key, (lon, lat, user_id_str))
                pipe.zadd(spec_last_upd_key, {user_id_str: now_int_ts})
            await pipe.execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Temporarily unable to update position")
    return {"status": "success", "message": "GPS position updated"}

## Alert messages endpoints (create, list)

@router.post("/api/alerts/{alert_id}/messages")
def create_alert_message(alert_id: int,
            message: MessageIn,
            request: Request,
            background_tasks: BackgroundTasks,
            current_user: User = Depends(get_current_user),
            db_session: Session = Depends(get_db_session)):
    # Only the alert sender (creator) or the chief alert manager can create messages for an alert
    # The messages will be visible to all alerted users, but only the sender and the chief manager can create messages
    alert = db_session.exec(select(Alert).where(Alert.id == alert_id)).first()
    if (not alert) or (not alert.id):
        raise not_found_exception("Alert not found")
    if alert.is_closed:
        raise forbidden_exception("Alert is closed, you can't create messages for it")
    # If the caller (current_user) is not the alert sender
    # and is not the alerted manager, the API call is not authorized
    if (current_user.id != alert.user_id):
        statement = (select(AlertedUser)
            .where(AlertedUser.alert_id == alert.id, AlertedUser.user_id == current_user.id)
            .where(AlertedUser.is_manager == True))
        alerted_manager = db_session.exec(statement).first()
        if not alerted_manager:
            raise forbidden_exception("Only the alert sender or the chief alert manager can create messages for this alert")
    # If the sender of a local alert is not reliable or the alert is bannned,
    # the sender cannot write any messages.
    if (alert.type == AlertType.local.value) and (current_user.id == alert.user_id):
        if ((not current_user.is_reliable) or (current_user.reliability_score <= 0)):
            raise forbidden_exception("You are not a reliable user, you can't create messages for this alert")
        if alert.is_banned:
            raise forbidden_exception("This alert has been banned, you can't create messages for it")
    if alert.messages_num >= ALERT_MAX_MESSAGES_NUM:
        raise forbidden_exception(f"This alert has reached the maximum number of messages ({ALERT_MAX_MESSAGES_NUM}), you can't create more messages for it")
    # We create the message and increment the messages_num field in the alert 
    # (see details about denormalization in the Alert model, at "messages_num" field).
    new_message = Message(
        alert_id=alert.id,
        user_id=current_user.id,
        content=message.content
    )
    db_session.add(new_message)
    alert.messages_num += 1
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(new_message)
    # For local and managed alerts, we call the background task 
    # to notify all users involved in the alert (except current_user)
    if (alert.type == AlertType.local.value) or (alert.type == AlertType.managed.value):
        alert_copy = Alert.model_validate(alert)
        curr_user_copy = User.model_validate(current_user)
        message_copy = Message.model_validate(new_message)
        req_info = get_request_info(str(current_user.id))
        background_tasks.add_task(
            task_alert_notify_on_new_message,
            alert_copy,
            message_copy,
            curr_user_copy, 
            request_info=req_info,
            db_engine=request.app.state.db_engine)
    return { "message": "Message created successfully", "message_id": new_message.id }

@router.get("/api/alerts/{alert_id}/messages", response_model=list[MessageOut])
def get_alert_messages(alert_id: int,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session)):
    # If the alert is not found, we return "not found"
    statement = select(Alert).where(Alert.id == alert_id)
    alert = db_session.exec(statement).first()
    if (not alert) or (not alert.id):
        raise not_found_exception("Alert not found")
    statement = (select(AlertedUser)
            .where(AlertedUser.alert_id == alert_id))
    alerted_users = db_session.exec(statement).all()
    curr_user_is_alert_sender = (current_user.id == alert.user_id)
    curr_user_is_alerted_user = False
    alert_sender_id = alert.user_id
    alerted_manager_id = None
    for au in alerted_users:
        if au.user_id == current_user.id:
            curr_user_is_alerted_user = True
        if au.is_manager:
            alerted_manager_id = au.user_id
    # Only the alert sender (alert creator) or any alerted user can view the messages for an alert, 
    # but admins or a chiefs can view the messages anyway
    if (not current_user.is_admin) and (not current_user.is_chief):
        if (not curr_user_is_alert_sender) and (not curr_user_is_alerted_user):
            raise forbidden_exception("You are not authorized to view the messages for this alert")
    # Retrieve the messages for the alert
    statement = (select(Message, User)
            .join(User, Message.user_id == User.id) # type: ignore
            .where(Message.alert_id == alert_id)
            .order_by(asc(Message.created_at))
            )
    results = db_session.exec(statement).all()
    messages_out: list[MessageOut] = []
    for res in results:
        message = res[0]
        user = res[1]
        if message.is_banned:
            message.content = "[BANNED MESSAGE]"
        user_is_manager = ((alerted_manager_id and (user.id == alerted_manager_id)) 
                                or ((user.id == alert_sender_id) and (alert.type != AlertType.local.value)))
        msg_out = MessageOut(
            firstname=user.firstname,
            surname=user.surname,
            user_role=user.role,
            is_alert_sender=(user.id == alert_sender_id),
            is_alert_manager=user_is_manager,
            is_caller=(user.id == current_user.id),
            id=message.id,
            alert_id=alert.id,
            is_banned=message.is_banned,
            created_at=message.created_at,
            content=message.content)
        messages_out.append(msg_out)
    return messages_out
