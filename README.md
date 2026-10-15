# Keen

The open GLM desk. Facts run here. A split vote escalates. The model's words stay.

Version 1.0.0.

GLM-5 is a 744B mixture-of-experts model, about 40B parameters active, trained for long agent work. Those weights do not fit a 6GB GPU. Keen does not download them and does not pretend to be a new weight. The flagship it calls is `glm-5.3` at `https://api.z.ai/api/paas/v4/chat/completions`. You bring the key.

What Keen adds is the part a giant model is bad at: knowing when not to speak.

A fact about this machine is answered in this process. A decision is three votes on a fast seat. The confidence is the share that agreed. A number the model prints after the label is ignored. Unanimous keeps the label and GLM is not called. A split, a failed sample, or a dark fast seat goes to GLM. The text GLM returns is stored and shown as it arrived. There is no second pass and no refusal list.

## The card

This is one hostname, one unanimous decision, and a prove, on the machine it was built on, 2026-10-15. The decision was three local votes of the word `ship`. GLM was not called.

```
+--------------------------------------------------------------+
|                                                              |
| KEEN                                                         |
| the open glm desk                                            |
| facts run here. a split vote escalates.                      |
| the model's words are not rewritten.                         |
|                                                              |
+--------------------------------------------------------------+
+--------------------------------------------------------------+
| KEEN                                                  lap 01 |
| HANDS                                                MACHINE |
|                                                              |
| 0.08 ms                                                      |
|                                                              |
| ASK                                                          |
| hostname                                                     |
| DID                                                          |
| DjBFs                                                        |
|                                                              |
| STAMP  2be589e3                                              |
+--------------------------------------------------------------+
+--------------------------------------------------------------+
| KEEN                                                  lap 02 |
| JUDGE                                              UNANIMOUS |
|                                                              |
| 0.04 ms                                                      |
| agree 1.0000                                                 |
|                                                              |
| ASK                                                          |
| choose ship|hold :: the tests are green                      |
| DID                                                          |
| ship                                                         |
| VOTES                                                        |
| ship ship ship                                               |
|                                                              |
| STAMP  a1064fe1                                              |
+--------------------------------------------------------------+
+--------------------------------------------------------------+
| KEEN                                                  lap 03 |
| PROVE                                              WITNESSED |
|                                                              |
| 8.02 ms                                                      |
|                                                              |
| ASK                                                          |
| prove                                                        |
| DID                                                          |
| facts checked 1                                              |
| witnessed 1                                                  |
| drifted 0                                                    |
| tampered 0                                                   |
| left alone 1                                                 |
| model laps are not re-run. a model is not a fact.            |
|                                                              |
| STAMP  ef273e12                                              |
+--------------------------------------------------------------+
```

`stamp 2be589e3` finds that hostname lap again. If the line in the file no longer matches its code, prove says tampered. The judge lap is not a fact, so prove left it alone.

## Measured

On 2026-10-15, 40 hostname reads took 0.0199 ms in this process. The same 40 asks through a loopback HTTP server that returns at once took 1.7957 ms. No model was loaded. A cloud GLM call is slower than that empty hop, because the hop is only the socket.

```
python -m keen bench
```

The bench line prints two decimals. The numbers above are the same run, printed to four decimals, so 0.02 ms on the bench line is this 0.0199 ms and not a different claim.

## Commands

```
python -m keen hostname
python -m keen choose yes|no :: ship it
python -m keen pit
python -m keen prove
python -m keen bench
python -m keen stamp 2be589e3
python -m keen seats
```

`choose a|b|c :: the question` takes 3 votes. The fast seat is `KEEN_FAST_URL`, an OpenAI-compatible chat completion. Unanimous means all 3 samples named the same label. A sample that errors counts in the denominator, so a crash lowers the share instead of vanishing. Two out of three is not enough. The lap goes to GLM with the original line as the user message.

`prove` re-runs hostname, whoami, cwd, disk, and python. The same answer is witnessed. A different answer drifted. `list`, `read`, and `run` are left alone. A model lap is not a fact.

`run` is an argument list, not a shell. Quoted `a&b` is one argument.

## Seats

| name | where |
| --- | --- |
| glm | `KEEN_GLM_URL`, or `https://api.z.ai/api/paas/v4/chat/completions` |
| model | `KEEN_GLM_MODEL`, or `glm-5.3` |
| key | `KEEN_GLM_KEY`, or `ZHIPU_API_KEY` |
| fast | `KEEN_FAST_URL` and `KEEN_FAST_MODEL` |

A key is not printed and it is not written into a lap. With no key, a public URL is not called. The lap says `seat dark: glm has no key`. A loopback URL may run without a key.

The lap file is `~/.keen/laps.jsonl`. The last card is `~/.keen/keen.txt`. A line carries `v`, `t`, `lap`, `lane`, `ask`, `did`, `ms`, `proof`, `stamp`, `agree`, and `votes`. The lanes are `hands`, `judge`, `glm`, and `prove`.

## What this is

Three lessons already measured on one machine, put in front of GLM.

Facts that can be executed should be executed. That is the hands lane.

A confidence the model states can sit on one number for every item. Keen does not read that number. Confidence is the vote share. Agreement is stability, not proof the label is true. A failed sample dilutes the share. That is the judge.

The weight people asked for is GLM. Keen calls it last, and it does not rewrite the reply. A provider's own rules still apply on that provider's API. Keen does not remove them, and it does not retry until the words change.

Orbits 2 is the multi-seat pit. Keen is the GLM desk. They do not import each other. A fact in either one runs in process.

## What this is not

This is not a 744B checkpoint. It will not beat GLM-5, or anyone else, on a coding bench, because on open language it is GLM. It beats the habit of asking that model what the hostname is.

Do not type a password into a lap. `read` stores the file. Point it at work you are willing to keep.

There is no moderation pass. The seat's text is the answer.

## Test

```
python tests/test_keen.py
```

24 tests. No live model. Python 3.10 or newer. The standard library is enough.

## License

MIT. Christian Rivera (DJ BrightFuture).
