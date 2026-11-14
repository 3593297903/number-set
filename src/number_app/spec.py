from dataclasses import dataclass

@dataclass(frozen=True)
class BatchSpec:
    copies: int
    group_count: int

    def __post_init__(self):
        if type(self.copies) is not int or type(self.group_count) is not int:
            raise ValueError("套数和组数必须是整数")
        if not 100 <= self.copies <= 300 or not 40 <= self.group_count <= 300:
            raise ValueError("套数须为100～300，组数须为40～300")
        if not self.group_count * self.lower <= self.total <= self.group_count * self.upper:
            raise ValueError("配额不可行")

    @property
    def total(self): return 1000 * self.copies
    @property
    def lower(self): return 2 * self.copies
    @property
    def upper(self): return 30 * self.copies
