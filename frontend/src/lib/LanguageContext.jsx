import React, { useMemo } from "react";
import { translate } from "./i18n";
import { LanguageContext } from "./useTranslation";

export function LanguageProvider({ lang = "en", children }) {
  const value = useMemo(() => ({
    lang,
    t: (key, vars) => translate(lang, key, vars),
  }), [lang]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}
