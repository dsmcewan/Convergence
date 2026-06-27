# UI How-To Research Pack

This project should treat UI polish as a repeatable evidence gate: design, build, browser-test, and regression-test across every corpus and view.

## Primary References

- W3C WCAG 2.2 Quick Reference: https://www.w3.org/WAI/WCAG22/quickref/
- WAI-ARIA Authoring Practices Guide: https://www.w3.org/WAI/ARIA/apg/patterns/
- Nielsen Norman Group 10 Usability Heuristics: https://www.nngroup.com/articles/ten-usability-heuristics/
- Material Design 3: https://m3.material.io/
- Apple Human Interface Guidelines: https://developer.apple.com/design/human-interface-guidelines
- Microsoft Fluent 2: https://fluent2.microsoft.design/
- GOV.UK Design System: https://design-system.service.gov.uk/
- IBM Carbon Design System: https://carbondesignsystem.com/
- React official docs via Context7 library `/reactjs/react.dev`: https://react.dev/

## TELOS UI Gate

1. Define the screen job, audience, and first-screen promise.
2. Build an acceptance matrix across every corpus, slide, viewport, and interaction state.
3. Verify data truth through both static artifacts and live API routes.
4. Check hover, focus, click, keyboard, disabled, empty, loading, and error states.
5. Screenshot desktop and narrow/mobile viewports.
6. Turn every correction into a regression test.
7. Do not report polish without fresh command output and live browser evidence.

## React Carryover For Other Projects

When the project is React-based, apply the same UI gate through component contracts:

- Load current React docs through Context7 before API-sensitive work.
- Separate data hooks from display components.
- Keep components pure and avoid duplicated derived state.
- Use stable keys for evidence rows, slides, tabs, messages, and animations.
- Treat hover/focus/click behavior as component API, not incidental CSS.
- Use Testing Library for component behavior and Playwright/browser checks for whole-flow proof.

## Convergence Demo Standards

- A pattern requires more than three unique chronological records.
- A behavior/pattern/campaign hierarchy must not duplicate source records accidentally.
- Highlighted fragments must map to human-readable translation and source evidence.
- Every hover reveal needs an equivalent focus reveal.
- User-facing copy should avoid raw engine labels unless the view is explicitly an engine/debug panel.
