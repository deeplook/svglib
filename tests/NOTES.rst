.. -*- mode: rst -*-

Notes
=====

This is a list to keep track of remaining issues observed via eye-ball
testing for various files.


misc
----

The remaining issues here are mostly related to gradient fillings.

- Python_logo_and_wordmark.svg


wikipedia/flags
---------------

The remaining issues are all related to gradient fillings.

- Belize.svg
- Ecuador.svg
- Guatemala.svg
- Mexico.svg
- Nicaragua.svg


wikipedia/symbols
-----------------

Issues here are often very small and related to text. (The map examples
should perhaps go into a seperate folder.)

- CO2_responsibility_1950-2000.svg (text)





That is a fascinating and important point to raise. The suggestion from Copilot Autofix is incorrect, and following it would break the code.

  Let's walk through why.

  Here is the code block in question (I'll use the T block as an example, but the logic is identical for Q, q, and t):

   1 # ...
   2 x0, y0 = points[-2:]  # <-- Copilot suggests removing THIS line.
   3 xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
   4 last_quadratic_cp = (xi, yi)
   5 xn, yn = nums
   6 (x0, y0), (x1, y1), (x2, y2), (xn, yn) = convert_quadratic_to_cubic_path(
   7     (x0, y0), (xi, yi), (xn, yn)
   8 )
   9 path.curveTo(x1, y1, x2, y2, xn, yn)

  Why Copilot's Suggestion is Wrong

  If we follow the suggestion and remove the line x0, y0 = points[-2:], the very next line will fail:

   1 xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)

  When Python tries to execute this line, it will immediately raise a NameError because the variables x0 and y0 have not been defined yet. They are needed as input for this calculation, which happens before the
  call to convert_quadratic_to_cubic_path.

  The Real Redundancy

  The actual redundancy, which CodeQL correctly identified and my fix addressed, is in the unpacking of the return value.

   1. We need `x0, y0`: We get them from points[-2:].
   2. We use `x0, y0`: We use them to calculate xi, yi and then pass them into convert_quadratic_to_cubic_path.
   3. The function returns `(x0, y0)`: The function's first return value is simply the same (x0, y0) that we just gave it.
   4. The original code re-assigns them: The line (x0, y0), ... = ... takes this returned value and pointlessly assigns it back to the variables that already hold it.

  My fix correctly identifies that the return value is what's redundant, not the initial assignment. By changing the unpacking to (_, _), ... = ..., we keep the necessary initial assignment and discard the
  unnecessary return value.

  In short, Copilot Autofix misidentified which assignment was the redundant one. Following its advice would crash the program.
