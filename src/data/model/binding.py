from dataclasses import dataclass


class BindStatus:
    UNBOUNDED = 0
    BINDING = 1
    BOUND = 2


@dataclass
class Binding:
    establish_binding_time: int
    bind_status: int
