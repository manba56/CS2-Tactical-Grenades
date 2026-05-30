export function useHead(title: string, description: string, image?: string) {
  document.title = `${title} — CS2 Tactics Lab`;

  const setMeta = (attr: string, value: string, isProperty: boolean) => {
    const selector = isProperty
      ? `meta[property="${attr}"]`
      : `meta[name="${attr}"]`;
    let el = document.querySelector(selector) as HTMLMetaElement | null;
    if (!el) {
      el = document.createElement('meta');
      if (isProperty) el.setAttribute('property', attr);
      else el.setAttribute('name', attr);
      document.head.appendChild(el);
    }
    el.setAttribute('content', value);
  };

  setMeta('description', description, false);
  setMeta('og:title', `${title} — CS2 Tactics Lab`, true);
  setMeta('og:description', description, true);
  if (image) setMeta('og:image', image, true);
}
