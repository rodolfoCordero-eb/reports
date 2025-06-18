from abc import ABC,abstractmethod

class DrawStrategy(ABC):
    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def run(self,session,acc_id, acc_name,path):
        pass

