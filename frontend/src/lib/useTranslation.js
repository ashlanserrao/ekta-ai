import { createContext, useContext } from "react";
import { translate } from "./i18n";

// Context + hook live here (a component-free module) so LanguageContext.jsx only
// exports the provider component and stays compatible with React Fast Refresh.
export const LanguageContext = createContext({
  lang: "en",
  t: (key, vars) => translate("en", key, vars),
});

export function useTranslation() {
  return useContext(LanguageContext);
}
