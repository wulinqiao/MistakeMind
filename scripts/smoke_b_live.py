"""One explicit two-call real-service diagnosis; requires --live."""
import argparse
import json

from agents.config import Settings
from agents.pipeline import AgentService
from schemas.models import AgentContext


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--sentence", default="我们在图书馆安静地阅读。")
    args = parser.parse_args()
    settings = Settings.from_env()
    if settings.resolved_mode != "live":
        parser.error("需要本地配置真实密钥、模型名及 live/auto 模式。")
    result = AgentService(settings).diagnose(AgentContext(request_id="live-smoke", user_id="synthetic_demo",
        task="diagnose", sentence=args.sentence, need_hints=False, grade="初中"))
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
