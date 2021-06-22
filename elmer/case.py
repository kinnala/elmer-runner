import tempfile

from typing import Optional

from numpy import ndarray

from .runners.docker import run
from .mesh import to_file


class Case:

    def __init__(self,
                 mesh,
                 sif,
                 t_id: Optional[ndarray] = None,
                 boundary_id: Optional[ndarray] = None):

        self.mesh = mesh
        self.sif = sif
        self.t_id = t_id
        self.boundary_id = boundary_id

    def run(self,
            verbose: bool = False,
            image: str = 'elmer',
            tag: str = 'latest',
            fetch: Optional[str] = None):

        retval = None

        with tempfile.TemporaryDirectory() as dirpath:
            to_file(
                self.mesh,
                "{}/tmpmesh".format(dirpath),
                self.t_id,
                self.boundary_id,
            )
            retval = run(
                "{}/tmpmesh".format(dirpath),
                self.sif,
                verbose=verbose,
                image=image,
                tag=tag,
                fetch=fetch,
            )

        return retval
