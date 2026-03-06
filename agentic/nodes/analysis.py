import torch
import cv2
from PIL import Image
from transformers import AutoProcessor, AutoModelForCausalLM
from unittest.mock import patch
from transformers.dynamic_module_utils import get_imports

class AnalysisNode:
    """Florence-2 VLM 기반 장면 분석"""

    def __init__(self, model_id: str = "microsoft/Florence-2-base"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Flash attention bypass
        def fixed_get_imports(filename):
            if not str(filename).endswith("modeling_florence2.py"):
                return get_imports(filename)
            imports = get_imports(filename)
            if "flash_attn" in imports:
                imports.remove("flash_attn")
            return imports

        with patch("transformers.dynamic_module_utils.get_imports", fixed_get_imports):
            self.model = AutoModelForCausalLM.from_pretrained(
                model_id,
                trust_remote_code=True,
                attn_implementation="sdpa"
            ).to(self.device).eval()

        self.processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)

    def process(self, state: dict) -> dict:
        """프레임 분석 후 state 업데이트"""
        frame = state.get("frame")
        if frame is None:
            return self._empty_result()

        # BGR -> RGB -> PIL
        image_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        # VLM 분석
        task_prompt = "<MORE_DETAILED_CAPTION>"
        inputs = self.processor(text=task_prompt, images=image_pil, return_tensors="pt").to(self.device)

        generated_ids = self.model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=512,
            do_sample=False,
            num_beams=3,
        )

        text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

        # 결과 파싱
        return self._parse_description(text)

    def _parse_description(self, text: str) -> dict:
        """텍스트에서 연령, 위치, 위험요소 추출"""
        text_lower = text.lower()

        # 연령 추정
        if any(word in text_lower for word in ["elderly", "old", "senior", "aged"]):
            age = "elderly"
        elif any(word in text_lower for word in ["child", "kid", "young"]):
            age = "child"
        else:
            age = "adult"

        # 위치 추정
        if any(word in text_lower for word in ["stair", "steps"]):
            location = "stairs"
        elif any(word in text_lower for word in ["bathroom", "toilet", "shower"]):
            location = "bathroom"
        elif any(word in text_lower for word in ["outdoor", "outside", "street"]):
            location = "outdoor"
        elif any(word in text_lower for word in ["hallway", "corridor"]):
            location = "hallway"
        else:
            location = "other"

        # 위험요소
        hazards = []
        if "wet" in text_lower:
            hazards.append("wet floor")
        if "dark" in text_lower:
            hazards.append("poor lighting")
        if any(word in text_lower for word in ["obstacle", "clutter"]):
            hazards.append("obstacles")

        return {
            "scene_description": text,
            "estimated_age": age,
            "location_type": location,
            "hazards_detected": hazards,
        }

    def _empty_result(self) -> dict:
        return {
            "scene_description": "",
            "estimated_age": "unknown",
            "location_type": "other",
            "hazards_detected": [],
        }
