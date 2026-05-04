import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const token = request.cookies.get("menuai_admin_token")?.value;
  const apiKey = request.cookies.get("menuai_admin_api_key")?.value;

  const isAuth = !!token || !!apiKey;
  const isLogin = request.nextUrl.pathname === "/login";

  if (!isAuth && !isLogin) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (isAuth && isLogin) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api).*)"],
};
