"""Run the case in a container."""

import os
import tarfile
import tempfile
import json

import docker


def get_container(image: str = 'elmer',
                  tag: str = 'latest'):
    """Pull and/or start a container that has `ElmerSolver`.

    Parameters
    ----------
    image
        The container image name to use.
    tag

    Returns
    -------
    An object representing the container.

    """
    client = docker.from_env()

    # TODO pull image if not present
    #for line in client.api.pull(image,
    #                            tag=tag,
    #                            stream=True,
    #                            decode=True):
    #    if "status" in line:
    #        print(line["status"])

    ctr = client.containers.create(image,
                                   command='sleep infinity',
                                   detach=True)
    ctr.start()

    return ctr


def clean_container(ctr):
    """Kill and remove the container."""
    ctr.kill()
    ctr.remove()


def write_to_container(ctr,
                       content: str,
                       filename: str = None,
                       suffix: str = ".sif") -> str:
    """Write a given string to a file inside the container.

    Parameters
    ----------
    ctr
    content
    filename
    suffix

    Returns
    -------
    The filename of the file written inside the container.

    """
    # write string to a temporary file on host
    tmpfile = tempfile.NamedTemporaryFile(suffix=suffix,
                                          mode='w',
                                          delete=False)
    tmpfile.write(content)
    tmpfile.seek(0)
    tmpfile.close()

    # create a tar archive
    tarname = tmpfile.name + ".tar"
    tar = tarfile.open(tarname, mode='w')
    if filename is None:
        filename = tmpfile.name
    try:
        tar.add(tmpfile.name,
                arcname=os.path.basename(filename))
    finally:
        tar.close()
        os.remove(tmpfile.name)

    # unpack tar contents to container root
    with open(tarname, 'rb') as fh:
        ctr.put_archive("/", fh.read())

    os.remove(tarname)

    return "/" + os.path.basename(tmpfile.name)


def fetch_from_container(ctr, filename: str):
    """Fetch a file from container.

    Parameters
    ----------
    ctr
    filename

    Returns
    -------
    Mesh object from `meshio`.

    """
    tmpfile = tempfile.NamedTemporaryFile(suffix=".tar",
                                          mode='wb',
                                          delete=False)
    bits, _ = ctr.get_archive("{}".format(filename))
    basename = os.path.basename(filename)
    try:
        for chunk in bits:
            tmpfile.write(chunk)
        tmpfile.seek(0)
        tmpfile.close()
        tar = tarfile.open(tmpfile.name, mode='r')
        tar.extract(basename, tmpfile.name + "_out")
    finally:
        tar.close()
        os.remove(tmpfile.name)

    mesh = meshio.read(tmpfile.name + "_out/" + basename)
    os.remove(tmpfile.name + "_out/" + basename)
    os.rmdir(tmpfile.name + "_out")

    return mesh


def run(filename,
        sif: str,
        verbose: bool = False,
        image: str = 'elmer',
        tag: str = 'latest'):
    """Run the case in Docker.

    Parameters
    ----------
    filename
        The mesh filename.
    sif
    verbose
    image
    tag

    """
    ctr = get_container(image=image, tag=tag)

    for ext in ['header', 'nodes', 'elements', 'boundary']:
        with open("{}.{}".format(filename, ext), 'r') as handle:
            _ = write_to_container(ctr, handle.read(), filename="mesh.{}".format(ext))
    filename = write_to_container(ctr, sif)
    _ = write_to_container(ctr, filename, filename="ELMERSOLVER_STARTINFO")

    res = ctr.exec_run("ElmerSolver",
                       stream=False,
                       demux=False)
    if verbose:
        print(res.output.decode('utf-8'))

    clean_container(ctr)
