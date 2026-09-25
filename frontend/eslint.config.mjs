import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypeScript from "eslint-config-next/typescript";

const config = [
  ...nextCoreWebVitals,
  ...nextTypeScript,
  { ignores: [".next/**", "out/**", "node_modules/**", "next-env.d.ts"] },
];

export default config;
