from backend.app.core.domain_loader import load_domain


def test_signalwave_domain_loads() -> None:
    domain = load_domain("signalwave")
    assert domain.manifest.id == "signalwave"
