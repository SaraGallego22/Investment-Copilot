from collaborative_partner.memory.schema import UserProfile


def test_user_profile_defaults():
    profile = UserProfile(user_id="u1")
    assert profile.preferences == {}
    assert profile.weak_points == []
    assert profile.notes == []


def test_user_profile_touch_updates_timestamp():
    profile = UserProfile(user_id="u1")
    first = profile.updated_at
    profile.touch()
    assert profile.updated_at >= first
