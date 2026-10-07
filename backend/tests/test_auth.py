"""Kiểm thử API xác thực — Giai đoạn 2 (F01, F02)."""


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ─── Đăng ký ─────────────────────────────────────────────────
def test_register_creates_user_with_role_user(client) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Trần Thị B", "email": "b@ptit.edu.vn", "password": "123456"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "b@ptit.edu.vn"
    assert body["role"] == "USER"
    assert "password" not in body and "password_hash" not in body


def test_register_normalizes_email(client) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"full_name": "Trần Thị B", "email": "  B@PTIT.Edu.VN ", "password": "123456"},
    )
    response = client.post(
        "/api/v1/auth/login", json={"email": "b@ptit.edu.vn", "password": "123456"}
    )

    assert response.status_code == 200


def test_register_rejects_duplicate_email(client, registered_user) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Người khác", "email": registered_user["email"], "password": "123456"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "EMAIL_EXISTS"


def test_register_rejects_short_password(client) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Trần Thị B", "email": "c@ptit.edu.vn", "password": "123"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_register_rejects_invalid_email(client) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Trần Thị B", "email": "khong-phai-email", "password": "123456"},
    )

    assert response.status_code == 422


# ─── Đăng nhập ───────────────────────────────────────────────
def test_login_returns_token_and_user(client, registered_user) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 8 * 3600
    assert body["user"]["email"] == registered_user["email"]
    assert body["access_token"]


def test_login_with_wrong_password_is_rejected(client, registered_user) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": "sai-mat-khau"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_login_with_unknown_email_gives_same_error(client) -> None:
    """Không tiết lộ email nào tồn tại trong hệ thống."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "khongtontai@ptit.edu.vn", "password": "123456"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"


# ─── /auth/me ────────────────────────────────────────────────
def test_me_returns_current_user(client, auth_token, registered_user) -> None:
    response = client.get("/api/v1/auth/me", headers=auth_header(auth_token))

    assert response.status_code == 200
    assert response.json()["email"] == registered_user["email"]


def test_me_without_token_is_unauthorized(client) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHORIZED"


def test_me_with_garbage_token_is_unauthorized(client) -> None:
    response = client.get("/api/v1/auth/me", headers=auth_header("khong-phai-jwt"))

    assert response.status_code == 401


# ─── Đăng xuất ───────────────────────────────────────────────
def test_logout_revokes_token(client, auth_token) -> None:
    assert client.post("/api/v1/auth/logout", headers=auth_header(auth_token)).status_code == 204

    response = client.get("/api/v1/auth/me", headers=auth_header(auth_token))
    assert response.status_code == 401
    assert "thu hồi" in response.json()["detail"]["message"]


def test_logout_does_not_affect_other_sessions(client, registered_user) -> None:
    """Mỗi lần đăng nhập có jti riêng nên chỉ token bị đăng xuất mới vô hiệu."""
    credentials = {"email": registered_user["email"], "password": registered_user["password"]}
    first = client.post("/api/v1/auth/login", json=credentials).json()["access_token"]
    second = client.post("/api/v1/auth/login", json=credentials).json()["access_token"]

    client.post("/api/v1/auth/logout", headers=auth_header(first))

    assert client.get("/api/v1/auth/me", headers=auth_header(first)).status_code == 401
    assert client.get("/api/v1/auth/me", headers=auth_header(second)).status_code == 200


def test_update_profile_persists_and_preserves_login(client, auth_token, registered_user):
    payload = {"full_name": "  Nguyễn Xuân Hùng  ", "student_id": " B23DCCN361 ",
               "school": "Học Viện Công Nghệ Bưu Chính Viễn Thông", "contact_email": "Hungmk2005@gmail.com"}
    response = client.patch("/api/v1/auth/me", json=payload, headers=auth_header(auth_token))
    assert response.status_code == 200
    body = response.json()
    assert body["student_id"] == "B23DCCN361"
    assert body["school"] == payload["school"]
    assert body["contact_email"].lower() == "hungmk2005@gmail.com"
    assert body["email"] == registered_user["email"]
    assert body["role"] == "USER"
    assert "password_hash" not in body
    assert client.get("/api/v1/auth/me", headers=auth_header(auth_token)).json() == body
    login = client.post("/api/v1/auth/login", json={"email": registered_user["email"], "password": registered_user["password"]})
    assert login.status_code == 200
    assert login.json()["user"]["student_id"] == "B23DCCN361"


def test_update_profile_only_changes_current_account(client, auth_token):
    client.post("/api/v1/auth/register", json={"full_name": "Người khác", "email": "other@example.com", "password": "123456"})
    other = client.post("/api/v1/auth/login", json={"email": "other@example.com", "password": "123456"}).json()["access_token"]
    payload = {"full_name": "Tên mới", "student_id": "NEW", "school": None, "contact_email": None}
    assert client.patch("/api/v1/auth/me", json=payload, headers=auth_header(auth_token)).status_code == 200
    unchanged = client.get("/api/v1/auth/me", headers=auth_header(other)).json()
    assert unchanged["full_name"] == "Người khác"
    assert unchanged["student_id"] is None


def test_update_profile_rejects_unauthenticated_and_privilege_fields(client, auth_token):
    payload = {"full_name": "Nguyễn Xuân Hùng"}
    assert client.patch("/api/v1/auth/me", json=payload).status_code == 401
    for invalid in ({"role": "ADMIN"}, {"email": "other@example.com"}, {"id": 2}, {"contact_email": "invalid"}, {"full_name": "   "}):
        response = client.patch("/api/v1/auth/me", json={**payload, **invalid}, headers=auth_header(auth_token))
        assert response.status_code == 422
    assert client.get("/api/v1/auth/me", headers=auth_header(auth_token)).json()["role"] == "USER"



def test_partial_profile_update_preserves_omitted_fields_and_can_clear(client, auth_token):
    headers = auth_header(auth_token)
    client.patch("/api/v1/auth/me", headers=headers, json={"full_name": "Tên ban đầu", "student_id": "B23DCCN361", "school": "PTIT"})
    updated = client.patch("/api/v1/auth/me", headers=headers, json={"full_name": "Tên mới"}).json()
    assert updated["student_id"] == "B23DCCN361"
    assert updated["school"] == "PTIT"
    cleared = client.patch("/api/v1/auth/me", headers=headers, json={"full_name": "Tên mới", "student_id": None, "school": " "}).json()
    assert cleared["student_id"] is None
    assert cleared["school"] is None
