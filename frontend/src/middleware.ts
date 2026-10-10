import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(req: NextRequest) {
  const token = req.cookies.get("nexusai_token")?.value ||
    req.headers.get("authorization")?.replace("Bearer ", "");

  const isAdminRoute = req.nextUrl.pathname.startsWith("/admin");
  const isAuthRoute  = req.nextUrl.pathname.startsWith("/login") ||
                       req.nextUrl.pathname.startsWith("/signup");

  if (isAdminRoute && !token) {
    return NextResponse.redirect(new URL("/login", req.url));
  }
  if (isAuthRoute && token) {
    return NextResponse.redirect(new URL("/admin/dashboard", req.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*", "/login", "/signup"],
};
