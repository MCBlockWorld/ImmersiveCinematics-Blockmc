#!/usr/bin/env python3
"""Camera script editor for Immersive Cinematics.

Standalone GUI editor with validation and structured panels for scripts,
shot rules, and movement routes.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


PATH_TYPES = [
    "DIRECT",
    "SMOOTH",
    "ORBIT",
    "BEZIER",
    "SPIRAL",
    "DOLLY_ZOOM",
    "STATIONARY_PAN",
]

DEFAULT_DIR = Path("src/main/resources/config/immersive_cinematics/camera_scripts")


@dataclass
class CameraScript:
    name: str = ""
    description: str = ""
    script_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    shot_rules: list[dict] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "CameraScript":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            script_id=data.get("id", str(uuid.uuid4())),
            shot_rules=data.get("shotRules", []),
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "id": self.script_id,
            "shotRules": self.shot_rules,
        }


class CameraScriptEditor(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Immersive Cinematics Script Editor")
        self.geometry("1200x760")

        self.script_dir = DEFAULT_DIR if DEFAULT_DIR.exists() else Path.cwd()
        self.script_paths: list[Path] = []
        self.current_path: Path | None = None
        self.script = CameraScript()
        self.current_rule_index: int | None = None
        self.current_route_index: int | None = None

        self._build_ui()
        self._refresh_script_list()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        root_frame = ttk.Frame(self, padding=10)
        root_frame.grid(row=0, column=0, sticky="nsew")
        root_frame.columnconfigure(1, weight=1)
        root_frame.rowconfigure(0, weight=1)

        self._build_left_panel(root_frame)
        self._build_right_panel(root_frame)

        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=1, column=0, sticky="ew")

    def _build_left_panel(self, parent: ttk.Frame) -> None:
        left_panel = ttk.Frame(parent)
        left_panel.grid(row=0, column=0, sticky="ns")

        ttk.Label(left_panel, text="脚本目录").pack(anchor=tk.W)
        dir_row = ttk.Frame(left_panel)
        dir_row.pack(fill=tk.X, pady=4)

        self.dir_var = tk.StringVar(value=str(self.script_dir))
        ttk.Entry(dir_row, textvariable=self.dir_var, width=36).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dir_row, text="选择...", command=self._choose_dir).pack(side=tk.LEFT, padx=4)
        ttk.Button(left_panel, text="刷新", command=self._refresh_script_list).pack(fill=tk.X)

        ttk.Label(left_panel, text="脚本列表").pack(anchor=tk.W, pady=(10, 0))
        self.script_list = tk.Listbox(left_panel, height=20)
        self.script_list.pack(fill=tk.BOTH, expand=True)
        self.script_list.bind("<<ListboxSelect>>", self._on_script_selected)

        button_row = ttk.Frame(left_panel)
        button_row.pack(fill=tk.X, pady=6)
        ttk.Button(button_row, text="新建", command=self._new_script).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(button_row, text="保存", command=self._save_script).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        ttk.Button(button_row, text="另存为", command=self._save_script_as).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _build_right_panel(self, parent: ttk.Frame) -> None:
        right_panel = ttk.Frame(parent)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(2, weight=1)

        script_meta = ttk.LabelFrame(right_panel, text="脚本信息", padding=10)
        script_meta.grid(row=0, column=0, sticky="ew")
        script_meta.columnconfigure(1, weight=1)

        self.name_var = tk.StringVar()
        self.desc_var = tk.StringVar()
        self.id_var = tk.StringVar()

        self._add_entry(script_meta, "名称", self.name_var, 0)
        self._add_entry(script_meta, "描述", self.desc_var, 1)
        self._add_entry(script_meta, "ID", self.id_var, 2)

        split_frame = ttk.Frame(right_panel)
        split_frame.grid(row=1, column=0, sticky="ew", pady=6)
        split_frame.columnconfigure(0, weight=1)
        split_frame.columnconfigure(1, weight=1)

        self._build_rules_panel(split_frame)
        self._build_routes_panel(right_panel)

    def _build_rules_panel(self, parent: ttk.Frame) -> None:
        rules_panel = ttk.LabelFrame(parent, text="Shot Rules", padding=8)
        rules_panel.grid(row=0, column=0, sticky="nsew")
        rules_panel.columnconfigure(0, weight=1)

        self.rule_list = tk.Listbox(rules_panel, height=12)
        self.rule_list.grid(row=0, column=0, sticky="nsew")
        self.rule_list.bind("<<ListboxSelect>>", self._on_rule_selected)

        rule_buttons = ttk.Frame(rules_panel)
        rule_buttons.grid(row=1, column=0, sticky="ew", pady=6)
        ttk.Button(rule_buttons, text="添加规则", command=self._add_rule).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(rule_buttons, text="删除规则", command=self._delete_rule).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        rule_detail = ttk.LabelFrame(parent, text="规则信息", padding=8)
        rule_detail.grid(row=0, column=1, sticky="nsew", padx=6)
        rule_detail.columnconfigure(1, weight=1)

        self.rule_name_var = tk.StringVar()
        self.rule_loop_var = tk.BooleanVar()
        self.rule_delay_var = tk.StringVar()

        self._add_entry(rule_detail, "规则名称", self.rule_name_var, 0)
        ttk.Checkbutton(rule_detail, text="循环播放", variable=self.rule_loop_var).grid(row=1, column=0, sticky=tk.W)
        self._add_entry(rule_detail, "延迟 (秒)", self.rule_delay_var, 2)

        ttk.Label(rule_detail, text="触发条件 (JSON 数组)").grid(row=3, column=0, sticky=tk.W)
        self.trigger_text = tk.Text(rule_detail, height=6)
        self.trigger_text.grid(row=4, column=0, columnspan=2, sticky="ew", pady=4)

        ttk.Button(rule_detail, text="应用规则修改", command=self._apply_rule_changes).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=4
        )

    def _build_routes_panel(self, parent: ttk.Frame) -> None:
        routes_panel = ttk.LabelFrame(parent, text="Routes", padding=8)
        routes_panel.grid(row=2, column=0, sticky="nsew")
        routes_panel.columnconfigure(1, weight=1)

        self.route_list = tk.Listbox(routes_panel, height=12)
        self.route_list.grid(row=0, column=0, rowspan=2, sticky="ns")
        self.route_list.bind("<<ListboxSelect>>", self._on_route_selected)

        route_buttons = ttk.Frame(routes_panel)
        route_buttons.grid(row=2, column=0, sticky="ew", pady=6)
        ttk.Button(route_buttons, text="添加路线", command=self._add_route).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(route_buttons, text="删除路线", command=self._delete_route).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        detail = ttk.Frame(routes_panel)
        detail.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=8)
        detail.columnconfigure(1, weight=1)

        self.route_name_var = tk.StringVar()
        self.path_type_var = tk.StringVar(value=PATH_TYPES[0])
        self.duration_var = tk.StringVar()
        self.start_fov_var = tk.StringVar()
        self.end_fov_var = tk.StringVar()
        self.start_yaw_var = tk.StringVar()
        self.start_pitch_var = tk.StringVar()
        self.end_yaw_var = tk.StringVar()
        self.end_pitch_var = tk.StringVar()
        self.speed_var = tk.StringVar()
        self.radius_var = tk.StringVar()
        self.height_var = tk.StringVar()
        self.strength_var = tk.StringVar()
        self.heading_var = tk.StringVar()
        self.forward_var = tk.BooleanVar(value=True)

        self._add_entry(detail, "路线名称", self.route_name_var, 0)
        ttk.Label(detail, text="路径类型").grid(row=1, column=0, sticky=tk.W)
        ttk.Combobox(detail, textvariable=self.path_type_var, values=PATH_TYPES, state="readonly").grid(
            row=1, column=1, sticky=tk.W
        )
        self._add_entry(detail, "持续时间 (秒)", self.duration_var, 2)
        self._add_entry(detail, "起始 FOV", self.start_fov_var, 3)
        self._add_entry(detail, "结束 FOV", self.end_fov_var, 4)
        self._add_entry(detail, "起始 Yaw", self.start_yaw_var, 5)
        self._add_entry(detail, "起始 Pitch", self.start_pitch_var, 6)
        self._add_entry(detail, "结束 Yaw", self.end_yaw_var, 7)
        self._add_entry(detail, "结束 Pitch", self.end_pitch_var, 8)
        self._add_entry(detail, "速度", self.speed_var, 9)
        self._add_entry(detail, "半径", self.radius_var, 10)
        self._add_entry(detail, "高度", self.height_var, 11)
        self._add_entry(detail, "强度", self.strength_var, 12)
        self._add_entry(detail, "朝向偏移 (度)", self.heading_var, 13)
        ttk.Checkbutton(detail, text="正向运动", variable=self.forward_var).grid(row=14, column=0, sticky=tk.W)

        vector_frame = ttk.LabelFrame(detail, text="向量 (x, y, z)")
        vector_frame.grid(row=15, column=0, columnspan=2, sticky="ew", pady=6)

        self.start_pos_vars = self._add_vector_row(vector_frame, "起点", 0)
        self.end_pos_vars = self._add_vector_row(vector_frame, "终点", 1)
        self.control_pos_vars = self._add_vector_row(vector_frame, "控制点", 2)
        self.target_pos_vars = self._add_vector_row(vector_frame, "目标点", 3)
        self.background_pos_vars = self._add_vector_row(vector_frame, "背景点", 4)

        ttk.Button(detail, text="应用路线修改", command=self._apply_route_changes).grid(
            row=16, column=0, columnspan=2, sticky="ew", pady=6
        )

    def _add_entry(self, parent: ttk.Frame, label: str, variable: tk.StringVar, row: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=2)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=2)

    def _add_vector_row(self, parent: ttk.Frame, label: str, row: int) -> tuple[tk.StringVar, tk.StringVar, tk.StringVar]:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, padx=2)
        vars_ = (tk.StringVar(), tk.StringVar(), tk.StringVar())
        ttk.Entry(parent, textvariable=vars_[0], width=7).grid(row=row, column=1, padx=2)
        ttk.Entry(parent, textvariable=vars_[1], width=7).grid(row=row, column=2, padx=2)
        ttk.Entry(parent, textvariable=vars_[2], width=7).grid(row=row, column=3, padx=2)
        return vars_

    def _choose_dir(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.script_dir)
        if selected:
            self.script_dir = Path(selected)
            self.dir_var.set(str(self.script_dir))
            self._refresh_script_list()

    def _refresh_script_list(self) -> None:
        self.script_list.delete(0, tk.END)
        if not self.script_dir.exists():
            self.status_var.set("脚本目录不存在")
            return
        self.script_paths = sorted(self.script_dir.glob("*.json"))
        for path in self.script_paths:
            self.script_list.insert(tk.END, path.name)
        self.status_var.set(f"找到 {len(self.script_paths)} 个脚本")

    def _on_script_selected(self, _event: tk.Event) -> None:
        if not self.script_list.curselection():
            return
        index = self.script_list.curselection()[0]
        self._load_script(self.script_paths[index])

    def _new_script(self) -> None:
        self.current_path = None
        self.script = CameraScript(name="new_script")
        self._populate_script_fields()
        self._refresh_rule_list()
        self._refresh_route_list()
        self.status_var.set("已创建新脚本")

    def _load_script(self, path: Path) -> None:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror("读取失败", f"无法读取脚本: {exc}")
            return
        self.current_path = path
        self.script = CameraScript.from_dict(raw)
        self._populate_script_fields()
        self._refresh_rule_list()
        self._refresh_route_list()
        self.status_var.set(f"已加载 {path.name}")

    def _populate_script_fields(self) -> None:
        self.name_var.set(self.script.name)
        self.desc_var.set(self.script.description)
        self.id_var.set(self.script.script_id)

    def _refresh_rule_list(self) -> None:
        self.rule_list.delete(0, tk.END)
        for rule in self.script.shot_rules:
            self.rule_list.insert(tk.END, rule.get("ruleName", "<unnamed>"))
        self.current_rule_index = None
        self._clear_rule_fields()

    def _refresh_route_list(self) -> None:
        self.route_list.delete(0, tk.END)
        for route in self._current_routes():
            self.route_list.insert(tk.END, route.get("routeName", "<unnamed>"))
        self.current_route_index = None
        self._clear_route_fields()

    def _current_rules(self) -> list[dict]:
        return self.script.shot_rules

    def _current_routes(self) -> list[dict]:
        if self.current_rule_index is None:
            return []
        if self.current_rule_index >= len(self.script.shot_rules):
            return []
        return self.script.shot_rules[self.current_rule_index].setdefault("routes", [])

    def _on_rule_selected(self, _event: tk.Event) -> None:
        if not self.rule_list.curselection():
            return
        self.current_rule_index = self.rule_list.curselection()[0]
        rule = self._current_rules()[self.current_rule_index]
        self.rule_name_var.set(rule.get("ruleName", ""))
        self.rule_loop_var.set(bool(rule.get("isLooping", False)))
        self.rule_delay_var.set(str(rule.get("delay", "")))
        self.trigger_text.delete("1.0", tk.END)
        self.trigger_text.insert("1.0", json.dumps(rule.get("triggerConditions", []), ensure_ascii=False, indent=2))
        self._refresh_route_list()

    def _on_route_selected(self, _event: tk.Event) -> None:
        if not self.route_list.curselection():
            return
        self.current_route_index = self.route_list.curselection()[0]
        route = self._current_routes()[self.current_route_index]
        self._populate_route_fields(route)

    def _populate_route_fields(self, route: dict) -> None:
        self.route_name_var.set(route.get("routeName", ""))
        self.path_type_var.set(route.get("pathType", PATH_TYPES[0]))
        self.duration_var.set(str(route.get("duration", "")))
        self.start_fov_var.set(str(route.get("startFOV", "")))
        self.end_fov_var.set(str(route.get("endFOV", "")))
        self.start_yaw_var.set(str(route.get("startYaw", "")))
        self.start_pitch_var.set(str(route.get("startPitch", "")))
        self.end_yaw_var.set(str(route.get("endYaw", "")))
        self.end_pitch_var.set(str(route.get("endPitch", "")))
        self.speed_var.set(str(route.get("speed", "")))
        self.radius_var.set(str(route.get("radius", "")))
        self.height_var.set(str(route.get("height", "")))
        self.strength_var.set(str(route.get("strength", "")))
        self.heading_var.set(str(route.get("heading", "")))
        self.forward_var.set(bool(route.get("isForward", True)))
        self._set_vector_vars(self.start_pos_vars, route.get("startPosition"))
        self._set_vector_vars(self.end_pos_vars, route.get("endPosition"))
        self._set_vector_vars(self.control_pos_vars, route.get("controlPosition"))
        self._set_vector_vars(self.target_pos_vars, route.get("targetPoint"))
        self._set_vector_vars(self.background_pos_vars, route.get("backgroundPoint"))

    def _set_vector_vars(self, vars_: tuple[tk.StringVar, tk.StringVar, tk.StringVar], value) -> None:
        if not isinstance(value, list) or len(value) != 3:
            for var in vars_:
                var.set("")
            return
        for var, coord in zip(vars_, value):
            var.set(str(coord))

    def _clear_rule_fields(self) -> None:
        self.rule_name_var.set("")
        self.rule_loop_var.set(False)
        self.rule_delay_var.set("")
        self.trigger_text.delete("1.0", tk.END)

    def _clear_route_fields(self) -> None:
        self.route_name_var.set("")
        self.path_type_var.set(PATH_TYPES[0])
        self.duration_var.set("")
        self.start_fov_var.set("")
        self.end_fov_var.set("")
        self.start_yaw_var.set("")
        self.start_pitch_var.set("")
        self.end_yaw_var.set("")
        self.end_pitch_var.set("")
        self.speed_var.set("")
        self.radius_var.set("")
        self.height_var.set("")
        self.strength_var.set("")
        self.heading_var.set("")
        self.forward_var.set(True)
        for vars_ in [
            self.start_pos_vars,
            self.end_pos_vars,
            self.control_pos_vars,
            self.target_pos_vars,
            self.background_pos_vars,
        ]:
            self._set_vector_vars(vars_, None)

    def _add_rule(self) -> None:
        self.script.shot_rules.append({
            "ruleName": f"rule_{len(self.script.shot_rules) + 1}",
            "routes": [],
            "triggerConditions": [],
            "isLooping": False,
            "delay": 0.0,
        })
        self._refresh_rule_list()
        self.rule_list.selection_set(tk.END)
        self._on_rule_selected(None)

    def _delete_rule(self) -> None:
        if self.current_rule_index is None:
            return
        if self.current_rule_index < len(self.script.shot_rules):
            self.script.shot_rules.pop(self.current_rule_index)
            self._refresh_rule_list()
            self._refresh_route_list()

    def _apply_rule_changes(self) -> None:
        if self.current_rule_index is None:
            return
        if self.current_rule_index >= len(self.script.shot_rules):
            return
        rule = self.script.shot_rules[self.current_rule_index]
        rule["ruleName"] = self.rule_name_var.get().strip()
        rule["isLooping"] = bool(self.rule_loop_var.get())
        rule["delay"] = self._parse_float(self.rule_delay_var.get(), 0.0)
        try:
            rule["triggerConditions"] = json.loads(self.trigger_text.get("1.0", tk.END).strip() or "[]")
        except json.JSONDecodeError as exc:
            messagebox.showerror("触发条件错误", f"无法解析触发条件 JSON: {exc}")
            return
        self._refresh_rule_list()
        self.status_var.set("规则已更新")

    def _add_route(self) -> None:
        if self.current_rule_index is None:
            messagebox.showinfo("提示", "请先选择一个规则")
            return
        routes = self._current_routes()
        routes.append({
            "routeName": f"route_{len(routes) + 1}",
            "pathType": PATH_TYPES[0],
            "duration": 5.0,
            "startFOV": 70,
            "endFOV": 70,
            "startYaw": 0,
            "startPitch": 0,
            "endYaw": 0,
            "endPitch": 0,
            "speed": 1.0,
            "radius": 5.0,
            "height": 2.0,
            "strength": 1.0,
            "isForward": True,
            "heading": 0.0,
        })
        self._refresh_route_list()
        self.route_list.selection_set(tk.END)
        self._on_route_selected(None)

    def _delete_route(self) -> None:
        if self.current_rule_index is None or self.current_route_index is None:
            return
        routes = self._current_routes()
        if self.current_route_index < len(routes):
            routes.pop(self.current_route_index)
            self._refresh_route_list()

    def _apply_route_changes(self) -> None:
        if self.current_rule_index is None or self.current_route_index is None:
            return
        routes = self._current_routes()
        if self.current_route_index >= len(routes):
            return
        route = routes[self.current_route_index]
        route.update({
            "routeName": self.route_name_var.get().strip(),
            "pathType": self.path_type_var.get(),
            "duration": self._parse_float(self.duration_var.get(), 0.0),
            "startFOV": self._parse_float(self.start_fov_var.get(), 70.0),
            "endFOV": self._parse_float(self.end_fov_var.get(), 70.0),
            "startYaw": self._parse_float(self.start_yaw_var.get(), 0.0),
            "startPitch": self._parse_float(self.start_pitch_var.get(), 0.0),
            "endYaw": self._parse_float(self.end_yaw_var.get(), 0.0),
            "endPitch": self._parse_float(self.end_pitch_var.get(), 0.0),
            "speed": self._parse_float(self.speed_var.get(), 1.0),
            "radius": self._parse_float(self.radius_var.get(), 5.0),
            "height": self._parse_float(self.height_var.get(), 2.0),
            "strength": self._parse_float(self.strength_var.get(), 1.0),
            "isForward": bool(self.forward_var.get()),
            "heading": self._parse_float(self.heading_var.get(), 0.0),
        })
        self._apply_vector(route, "startPosition", self.start_pos_vars)
        self._apply_vector(route, "endPosition", self.end_pos_vars)
        self._apply_vector(route, "controlPosition", self.control_pos_vars)
        self._apply_vector(route, "targetPoint", self.target_pos_vars)
        self._apply_vector(route, "backgroundPoint", self.background_pos_vars)
        self._refresh_route_list()
        self.status_var.set("路线已更新")

    def _apply_vector(self, route: dict, key: str, vars_: tuple[tk.StringVar, tk.StringVar, tk.StringVar]) -> None:
        raw = [var.get().strip() for var in vars_]
        if all(value == "" for value in raw):
            route.pop(key, None)
            return
        route[key] = [self._parse_float(value, 0.0) for value in raw]

    def _parse_float(self, value: str, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _save_script(self) -> None:
        self._commit_script_fields()
        if self.current_path is None:
            self._save_script_as()
            return
        self._write_script(self.current_path)

    def _save_script_as(self) -> None:
        self._commit_script_fields()
        target = filedialog.asksaveasfilename(
            initialdir=self.script_dir,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not target:
            return
        self.current_path = Path(target)
        self._write_script(self.current_path)
        self._refresh_script_list()

    def _write_script(self, path: Path) -> None:
        try:
            path.write_text(json.dumps(self.script.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            messagebox.showerror("保存失败", f"无法保存脚本: {exc}")
            return
        self.status_var.set(f"已保存 {path.name}")

    def _commit_script_fields(self) -> None:
        self.script.name = self.name_var.get().strip()
        self.script.description = self.desc_var.get().strip()
        script_id = self.id_var.get().strip() or str(uuid.uuid4())
        self.script.script_id = script_id
        self.id_var.set(script_id)


def main() -> None:
    app = CameraScriptEditor()
    app.mainloop()


if __name__ == "__main__":
    main()
