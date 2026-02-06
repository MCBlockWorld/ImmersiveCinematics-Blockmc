package com.example.immersive_cinematics.handler;

import com.example.immersive_cinematics.director.CameraScriptStorage;
import com.example.immersive_cinematics.network.NetworkHandler;
import com.example.immersive_cinematics.network.TriggerCameraScriptPacket;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.network.chat.Component;

public final class ServerCommandHandler {

    private ServerCommandHandler() {
    }

    public static void registerCommands(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(Commands.literal("ic-run")
            .requires(source -> source.hasPermission(2))
            .executes(ctx -> {
                ctx.getSource().sendFailure(Component.literal("ic-run 仅支持客户端/单人环境"));
                return 0;
            })
        );

        dispatcher.register(Commands.literal("ic-shot")
            .requires(source -> source.hasPermission(2))
            .then(Commands.literal("list")
                .executes(ctx -> {
                    var scripts = CameraScriptStorage.getInstance().getAllScripts();
                    if (scripts.isEmpty()) {
                        ctx.getSource().sendSuccess(() -> Component.literal("没有找到镜头脚本"), false);
                    } else {
                        ctx.getSource().sendSuccess(() -> Component.literal("可用镜头脚本:"), false);
                        for (String name : scripts.keySet()) {
                            ctx.getSource().sendSuccess(() -> Component.literal("- " + name), false);
                        }
                    }
                    return 1;
                })
            )
            .then(Commands.literal("reload")
                .executes(ctx -> {
                    CameraScriptStorage.getInstance().hotReload();
                    ctx.getSource().sendSuccess(() -> Component.literal("镜头脚本已重载"), false);
                    return 1;
                })
            )
            .then(Commands.literal("play")
                .then(Commands.argument("name", StringArgumentType.string())
                    .executes(ctx -> {
                        String name = StringArgumentType.getString(ctx, "name");
                        if (!CameraScriptStorage.getInstance().hasScript(name)) {
                            ctx.getSource().sendFailure(Component.literal("镜头脚本未找到: " + name));
                            return 0;
                        }
                        if (ctx.getSource().getEntity() instanceof ServerPlayer player) {
                            NetworkHandler.sendToPlayer(new TriggerCameraScriptPacket(name), player);
                            ctx.getSource().sendSuccess(() -> Component.literal("已触发镜头脚本: " + name), false);
                            return 1;
                        }
                        ctx.getSource().sendFailure(Component.literal("该命令只能由玩家执行"));
                        return 0;
                    })
                )
            )
        );
    }
}
