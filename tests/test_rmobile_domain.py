from backend.app.core.domain_loader import load_domain


def test_rmobile_domain_loads() -> None:
    domain = load_domain("rmobile")
    assert domain.manifest.id == "rmobile"
