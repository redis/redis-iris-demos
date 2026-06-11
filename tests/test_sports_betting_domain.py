from pathlib import Path

from backend.app.core.domain_loader import load_domain


def test_sports_betting_domain_loads() -> None:
    domain = load_domain("sports-betting")
    assert domain.manifest.id == "sports-betting"
    assert Path(domain.manifest.branding.logo_path).exists()
    assert domain.manifest.branding.starter_prompts
    assert domain.manifest.guardrail is not None
    assert domain.manifest.seed_memories
    assert domain.manifest.seed_langcache
    assert domain.manifest.branding.theme.landing_bg


def test_sports_betting_data_generator_writes_expected_files(tmp_path: Path) -> None:
    domain = load_domain("sports-betting")
    result = domain.generate_demo_data(output_dir=tmp_path, update_env_file=False)
    assert result.env_updates["DEMO_USER_ID"] == "PLY_DEMO_001"
    assert result.env_updates["CTX_SURFACE_NAME"] == '"Sportsbook Context Surface"'
    assert result.env_updates["CTX_AGENT_NAME"] == '"Sports Desk Agent"'
    assert result.env_updates["REDIS_INSTANCE_NAME"] == '"Sports Desk Redis Cloud"'
    for spec in domain.get_entity_specs():
        assert (tmp_path / spec.file_name).exists()
