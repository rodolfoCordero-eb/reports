from abc import ABC,abstractmethod

class ActionStrategy(ABC):
    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def run(self,session,acc_id, acc_name):
        pass