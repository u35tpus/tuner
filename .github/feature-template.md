Create new branch for the feature code changes:

Update README file.
Add unit tests. Ensure that unit tests pass. 

Also normally i test with something like below:
python3 intonation_trainer.py ./tracks/piano/yesterday.yaml --verbose

So apart from unit tests also try to reproduce my testing and verify artefacts created using my manual testing.

I also verify by running locally "make test"

Then git commit and git push everything and create pull request into main branch.