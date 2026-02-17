"""Objetos de escena para sombreado universal (base escalable)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import math


@dataclass
class ObjetoEscena(ABC):
    x: float
    y: float
    altura: float

    @abstractmethod
    def calcular_sombra(self, azimut: float, elevacion: float) -> dict:
        """Devuelve geometría unificada de sombra."""


@dataclass
class ArbolEscena(ObjetoEscena):
    radio_copa: float

    def calcular_sombra(self, azimut: float, elevacion: float) -> dict:
        elev = max(1e-3, elevacion)
        largo = self.altura / max(math.tan(math.radians(elev)), 1e-6)
        dx = -largo * math.sin(math.radians(azimut))
        dy = -largo * math.cos(math.radians(azimut))
        return {
            "tipo": "arbol",
            "origen": (self.x, self.y),
            "centro_sombra": (self.x + dx, self.y + dy),
            "radio": self.radio_copa,
            "largo": largo,
        }


@dataclass
class EstructuraEscena(ObjetoEscena):
    tipo: str
    x1: float
    y1: float
    x2: float
    y2: float

    def calcular_sombra(self, azimut: float, elevacion: float) -> dict:
        elev = max(1e-3, elevacion)
        largo = self.altura / max(math.tan(math.radians(elev)), 1e-6)
        dx = -largo * math.sin(math.radians(azimut))
        dy = -largo * math.cos(math.radians(azimut))
        return {
            "tipo": "estructura",
            "forma": self.tipo,
            "base": ((self.x1, self.y1), (self.x2, self.y2)),
            "desplazamiento": (dx, dy),
            "largo": largo,
        }


def adaptar_objetos_escena(arboles: list, estructuras: list) -> list[ObjetoEscena]:
    objetos: list[ObjetoEscena] = []
    for arbol in arboles:
        objetos.append(
            ArbolEscena(
                x=float(getattr(arbol, "x", 0.0)),
                y=float(getattr(arbol, "y", 0.0)),
                altura=float(getattr(arbol, "h", getattr(arbol, "altura", 0.0))),
                radio_copa=float(getattr(arbol, "radio_copa", 0.0)),
            )
        )
    for estructura in estructuras:
        objetos.append(
            EstructuraEscena(
                x=float(getattr(estructura, "x1", 0.0)),
                y=float(getattr(estructura, "y1", 0.0)),
                altura=float(getattr(estructura, "altura", 0.0)),
                tipo=str(getattr(estructura, "tipo", "estructura")),
                x1=float(getattr(estructura, "x1", 0.0)),
                y1=float(getattr(estructura, "y1", 0.0)),
                x2=float(getattr(estructura, "x2", 0.0)),
                y2=float(getattr(estructura, "y2", 0.0)),
            )
        )
    return objetos