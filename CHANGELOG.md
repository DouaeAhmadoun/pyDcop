Changelog
=========

Format based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)

pyDCOP v0.1.2 [Unreleased]
--------------------------

### Added
- New `--restart` flag on `agent` cli command.
- New `--version` global option on cli.
- `--graph` option may be omitted in `distribute` cli command, when `--algo`
 is given.
- Add a lot of documentation : usage, command line reference, etc. 
- termination detection in solve command: the command returns if all 
  computations have finished.

### Fixed
- When stopping an agent, the ws-sever (for ui) was not closed properly.
- Issues causing delays when stopping the orchestrator.
- Invalid metrics containing management computations instead of agents
- Avoid some crashes during metrics computations (when stopping the system 
  when metrics are not ready yet)

## Modified
- domain type is now optional (in API and yaml DCOP format)
- agents can be given as a list or a dict in yaml

pyDCOP v0.1.0 - 2018-05-04
--------------------------

- First open source release.