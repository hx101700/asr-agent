import childProcess = require("node:child_process");
import { syncBuiltinESMExports } from "node:module";

const execFile = childProcess.execFile;

// 将 BL 2.1.0 的 Windows 登录开页交给其完整链接出口，由 Python 打开一次。
childProcess.execFile = ((...parameters: Parameters<typeof execFile>) => {
  const [file, args] = parameters;
  if (process.platform === "win32" && file === "cmd" && Array.isArray(args)
      && args.length === 4 && args[0] === "/c" && args[1] === "start" && args[2] === ""
      && typeof args[3] === "string"
      && args[3].startsWith("https://bailian.console.aliyun.com/console-login?")) {
    // BL 会捕获此错误、输出完整 URL，并继续维护原授权回调。
    throw new Error("MemoFlow opens the console URL through the Windows URL handler.");
  }
  return Reflect.apply(execFile, childProcess, parameters);
}) as typeof execFile;

syncBuiltinESMExports();
