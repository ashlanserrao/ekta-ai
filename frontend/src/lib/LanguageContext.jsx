import React, { createContext, useContext, useMemo } from "react";
import { translate } from "./i18n";

const LanguageContext = createContext({ lang: "en", t: (key, vars) => translate("en", key, vars) });

export function LanguageProvider({ lang = "en", children }) {
  const value = useMemo(() => ({
    lang,
    t: (key, vars) => translate(lang, key, vars),
  }), [lang]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useTranslation() {
  return useContext(LanguageContext);
}
