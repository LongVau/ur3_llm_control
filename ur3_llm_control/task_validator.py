class PlanValidator:
    # Whitelist các phần tử hợp lệ theo đề bài
    ALLOWED_SKILLS = ["home", "pick", "place"]
    ALLOWED_OBJECTS = ["red_cube", "yellow_cube", "blue_cube"]
    ALLOWED_ZONES = ["zone_a", "zone_b", "zone_c"]

    @classmethod
    def validate(cls, plan_json: dict) -> tuple[bool, str]:
        # 1. Kiểm tra format gốc JSON
        if not isinstance(plan_json, dict) or "plan" not in plan_json:
            return False, "Thiếu trường 'plan' ở tầng cao nhất của JSON."

        steps = plan_json.get("plan", [])
        if not isinstance(steps, list) or len(steps) == 0:
            return False, "Kế hoạch (plan) rỗng hoặc không phải dạng danh sách."

        # 2. Duyệt qua từng bước trong kế hoạch để kiểm tra
        for i, step in enumerate(steps):
            skill = step.get("skill")
            
            # Kiểm tra tên skill
            if skill not in cls.ALLOWED_SKILLS:
                return False, f"Bước {i+1}: Skill '{skill}' không tồn tại trong danh sách cho phép."

            # Kiểm tra tham số của pick
            if skill == "pick":
                obj = step.get("object")
                if obj not in cls.ALLOWED_OBJECTS:
                    return False, f"Bước {i+1}: Object '{obj}' không hợp lệ cho lệnh pick."

            # Kiểm tra tham số của place
            elif skill == "place":
                obj = step.get("object")
                zone = step.get("zone")
                if obj not in cls.ALLOWED_OBJECTS:
                    return False, f"Bước {i+1}: Object '{obj}' không hợp lệ cho lệnh place."
                if zone not in cls.ALLOWED_ZONES:
                    return False, f"Bước {i+1}: Zone '{zone}' không hợp lệ cho lệnh place."

        return True, "Hợp lệ"