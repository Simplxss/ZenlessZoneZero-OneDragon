from typing import Optional

from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID
)
from AppKit import NSRunningApplication, NSApplicationActivateIgnoringOtherApps

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.utils.log_utils import log


class PcGameWindow:

    def __init__(self, win_title: str,
                 standard_width: int = 1920,
                 standard_height: int = 1080):
        self.win_title: str = win_title
        self.standard_width: int = standard_width
        self.standard_height: int = standard_height
        self.standard_game_rect: Rect = Rect(0, 0, standard_width, standard_height)

        self._win_info: Optional[dict] = None
        self.init_win()

    def init_win(self) -> None:
        """初始化窗口信息"""
        windows = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
        self._win_info = None
        for w in windows:
            title = w.get('kCGWindowName', '')
            if self.win_title == title:
                self._win_info = w
                break

    @property
    def is_win_valid(self) -> bool:
        """窗口是否存在"""
        if self._win_info is None:
            self.init_win()
        return self._win_info is not None

    @property
    def is_win_active(self) -> bool:
        """窗口是否为前台"""
        if not self.is_win_valid:
            return False
        pid = self._win_info.get('kCGWindowOwnerPID')
        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
        return app.isActive() if app else False

    @property
    def is_win_scale(self) -> bool:
        """窗口是否缩放"""
        rect = self.win_rect
        if rect is None:
            return False
        return not (rect.width == self.standard_width and rect.height == self.standard_height)

    def active(self) -> bool:
        """激活窗口到前台"""
        if not self.is_win_valid:
            return False
        try:
            pid = self._win_info.get('kCGWindowOwnerPID')
            app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
            if not app:
                return False
            app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
            return True
        except Exception:
            log.error('切换到游戏窗口失败', exc_info=True)
            return False

    @property
    def win_rect(self) -> Optional[Rect]:
        """获取窗口在屏幕上的位置（macOS CGWindowBounds）"""
        if not self.is_win_valid:
            return None

        bounds = self._win_info.get("kCGWindowBounds", {})
        x = int(bounds.get("X", 0))
        y = int(bounds.get("Y", 0))
        width = int(bounds.get("Width", 0))
        height = int(bounds.get("Height", 0))

        # macOS 给的是 (x, y, width, height)
        TITLE_BAR_HEIGHT = 30 + 25  # 或者根据应用调整
        return Rect(x, y + TITLE_BAR_HEIGHT, x + width, y + height)
        # return Rect(x, y, x + width, y + height)
    
    def get_scaled_game_pos(self, game_pos: Point) -> Optional[Point]:
        """将游戏内坐标缩放成窗口内坐标（相对坐标）"""
        rect = self.win_rect
        if rect is None:
            return None

        # 缩放比例
        xs = rect.width / self.standard_width
        ys = rect.height / self.standard_height

        s_pos = Point(game_pos.x * xs, game_pos.y * ys)

        return s_pos if self.is_valid_game_pos(s_pos, rect=rect) else None

    def is_valid_game_pos(self, s_pos: Point, rect: Optional[Rect] = None) -> bool:
        """判断缩放后的游戏坐标是否在窗口内（相对坐标）"""
        if rect is None:
            rect = self.standard_game_rect  # 必须是 (0,0,width,height)

        return 0 <= s_pos.x <= rect.width and 0 <= s_pos.y <= rect.height

    def game2win_pos(self, game_pos: Point) -> Optional[Point]:
        """
        获取在屏幕中的坐标
        :param game_pos: 默认分辨率下的游戏窗口里的坐标
        :return: 当前分辨率下的屏幕中的坐标
        """
        rect = self.win_rect
        if rect is None:
            return None
        gp: Point = self.get_scaled_game_pos(game_pos)
        # 缺少一个屏幕边界判断 游戏窗口拖动后可能会超出整个屏幕
        return rect.left_top + gp if gp is not None else None
