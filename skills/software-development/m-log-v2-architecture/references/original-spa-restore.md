# original SPA 복원 시 유의사항

`public/app/`을 원본 `~/m-log/`에서 복사할 때 주의할 점:

## 자동 복원되는 삭제 파일

원본 `~/m-log/public/app/`에는 다음 의도적으로 삭제한 파일들이 존재함. `cp -r`로 복사하면 이 파일들이 다시 생김:

- `js/views/QuintaxView.js` — Quintax 서비스 종료
- `js/views/Just5View.js` — Just5 서비스 종료  
- `js/components/QuintaxReport.js` — Quintax 리포트 컴포넌트

## 복원 후 필수 조치

```bash
rm -f public/app/js/views/QuintaxView.js \\
      public/app/js/views/Just5View.js \\
      public/app/js/components/QuintaxReport.js
```

## 단, app.js에서 위 파일들을 import하고 있음

`public/app/js/app.js`에 다음 import 구문이 있음:
```js
import { QuintaxView } from './views/QuintaxView.js';
import { Just5View } from './views/Just5View.js';
```

파일을 삭제만 하면 JS 에러로 SPA가 로딩되지 않음. **반드시 stub 파일을 생성해야 함:**

```js
// public/app/js/views/QuintaxView.js
import { Component } from '../core/Component.js';
export class QuintaxView extends Component {
    template() { return `<div>서비스 종료</div>`; }
}
```

동일하게 `Just5View.js`도 stub 생성.

이 패턴을 따르면 old SPA가 에러 없이 동작하면서도 삭제된 페이지는 표시되지 않음.
