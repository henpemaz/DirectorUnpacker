##Director Unpacker

Unpacker and hopefully re-packer for Adobe Director 12 .dir projects, written in python. *Currently a WIP* due to how cursed the file format is...

Strongly based on the efforts from [ProjectorRays on Github](https://github.com/ProjectorRays/ProjectorRays) for parsing the Director12 file.

Aims to being able to unpack a .dir director project into individual resources for version control and collaboration.

myDotDir.dir would become:

- myDotDir
    - cast1
    - cast2
        - myimage.png
    - mycast
        - myscript.ls

